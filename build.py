#!/usr/bin/env python3
# Builds Kana Liga: a subset of Noto Sans JP Regular whose GSUB turns romaji
# into hiragana, and uppercase syllables into katakana. The source is
# CID-keyed CFF, so glyphs are only ever looked up through its cmap, then
# redrawn into a fresh name-keyed CFF font with our own glyph names. The
# feature file is generated from data/romaji.tsv and data/words.tsv, and so
# is dist/kana-liga.ts, the same conversion in JS.
#
# usage: build.py
# run fetch-source.py first

import json
import os
import shutil

from fontTools import subset
from fontTools.agl import UV2AGL
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont

#
# Constants
#

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE_FONT = os.path.join(ROOT, "source", "NotoSansJP-Regular.otf")
SOURCE_LICENSE = os.path.join(ROOT, "source", "OFL.txt")
ROMAJI_TABLE = os.path.join(ROOT, "data", "romaji.tsv")
WORD_TABLE = os.path.join(ROOT, "data", "words.tsv")
BUILD_DIR = os.path.join(ROOT, "build")
DIST_DIR = os.path.join(ROOT, "dist")
FEA_PATH = os.path.join(BUILD_DIR, "kana-liga.fea")
OTF_PATH = os.path.join(DIST_DIR, "KanaLiga-Regular.otf")
WOFF2_PATH = os.path.join(DIST_DIR, "KanaLiga-Regular.woff2")
TS_TEMPLATE = os.path.join(ROOT, "kana-liga.ts")
TS_PATH = os.path.join(DIST_DIR, "kana-liga.ts")

FAMILY_NAME = "Kana Liga"
STYLE_NAME = "Regular"
PS_NAME = "KanaLiga-Regular"
VERSION = "1.000"

CODEPOINTS = (
    list(range(0x20, 0x7F))
    + list(range(0x3040, 0x30A0))
    + list(range(0x30A1, 0x30F7))
    + [0x30FC, 0x3001, 0x3002, 0x300C, 0x300D]
)

VOWELS = "aeiou"
# letters that keep a preceding n from becoming ん
N_KEEPERS = VOWELS + "y"
# doubled consonants that turn into っ, n is handled by the syllabic n rule
SOKUON_CONSONANTS = "bcdfghjklmpqrstvwxyz"

SMALL_TSU = "っ"
SYLLABIC_N = "ん"
LONG_VOWEL = "ー"

# katakana sits 0x60 above the matching hiragana
KATAKANA_OFFSET = 0x60

#
# Functions
#

def glyphNameFor(codepoint):
    if codepoint in UV2AGL and codepoint < 0x80:
        return UV2AGL[codepoint]
    return f"uni{codepoint:04X}"


def readRomajiTable(path):
    table = []
    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            romaji, kana = line.split("\t")
            table.append((romaji, kana))
    return table


# A syllable typed all uppercase is katakana, so each row also exists as
# uppercase romaji to the katakana.
def katakanaTable(table):
    return [(romaji.upper(), toKatakana(kana)) for romaji, kana in table]


def toKatakana(kana):
    return "".join(chr(ord(char) + KATAKANA_OFFSET) if 0x3041 <= ord(char) <= 0x3096 else char for char in kana)


def subsetSource(path, codepoints):
    font = TTFont(path)
    options = subset.Options()
    options.layout_features = []
    options.drop_tables += ["GSUB", "GPOS", "GDEF", "BASE", "VORG", "vhea", "vmtx", "DSIG"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(font)
    return font


def sequenceGlyphName(kana, glyph_names):
    return "seq." + "_".join(glyph_names[ord(char)] for char in kana)


def buildFont(source, table):
    source_cmap = source.getBestCmap()
    source_glyphs = source.getGlyphSet()
    source_hmtx = source["hmtx"]

    glyph_names = {}
    for codepoint in CODEPOINTS:
        if codepoint in source_cmap:
            glyph_names[codepoint] = glyphNameFor(codepoint)

    missing = sorted({char for _, kana in table for char in kana if ord(char) not in glyph_names})
    if missing:
        raise SystemExit(f"kana in the table but not in the font: {missing}")

    # one empty temporary glyph per multi kana output, the yoon lookup
    # expands each into its real glyphs
    sequence_names = sorted({sequenceGlyphName(kana, glyph_names) for _, kana in table if len(kana) > 1})

    glyph_order = [".notdef"] + [glyph_names[cp] for cp in sorted(glyph_names)] + sequence_names
    char_strings = {}
    metrics = {}

    def addGlyph(name, source_name):
        width, lsb = source_hmtx[source_name]
        pen = T2CharStringPen(width, None)
        source_glyphs[source_name].draw(pen)
        char_strings[name] = pen.getCharString()
        metrics[name] = (width, lsb)

    addGlyph(".notdef", ".notdef")
    for codepoint, name in glyph_names.items():
        addGlyph(name, source_cmap[codepoint])
    for name in sequence_names:
        char_strings[name] = T2CharStringPen(0, None).getCharString()
        metrics[name] = (0, 0)

    source_os2 = source["OS/2"]
    source_hhea = source["hhea"]
    source_post = source["post"]
    copyright = source["name"].getDebugName(0)

    builder = FontBuilder(source["head"].unitsPerEm, isTTF=False)
    builder.updateHead(fontRevision=float(VERSION))
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap({cp: name for cp, name in glyph_names.items()})
    builder.setupCFF(PS_NAME, {"FullName": f"{FAMILY_NAME} {STYLE_NAME}", "FamilyName": FAMILY_NAME, "Weight": STYLE_NAME}, char_strings, {})
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=source_hhea.ascent, descent=source_hhea.descent, lineGap=source_hhea.lineGap)
    builder.setupNameTable({
        "copyright": f"{copyright} Kana Liga is a modified version of Noto Sans JP.",
        "familyName": FAMILY_NAME,
        "styleName": STYLE_NAME,
        "uniqueFontIdentifier": f"{PS_NAME};{VERSION}",
        "fullName": f"{FAMILY_NAME} {STYLE_NAME}",
        "version": f"Version {VERSION}",
        "psName": PS_NAME,
        "description": "Renders romaji as hiragana and katakana through OpenType ligatures. Derived from Noto Sans JP.",
        "licenseDescription": source["name"].getDebugName(13),
        "licenseInfoURL": "https://openfontlicense.org",
    })
    builder.setupOS2(
        usWeightClass=source_os2.usWeightClass,
        fsType=0,
        fsSelection=source_os2.fsSelection,
        sTypoAscender=source_os2.sTypoAscender,
        sTypoDescender=source_os2.sTypoDescender,
        sTypoLineGap=source_os2.sTypoLineGap,
        usWinAscent=source_os2.usWinAscent,
        usWinDescent=source_os2.usWinDescent,
        sxHeight=source_os2.sxHeight,
        sCapHeight=source_os2.sCapHeight,
        achVendID="NONE",
    )
    builder.setupPost(underlinePosition=source_post.underlinePosition, underlineThickness=source_post.underlineThickness)

    font = builder.font
    font["OS/2"].recalcUnicodeRanges(font)
    font["OS/2"].recalcCodePageRanges(font)
    return font, glyph_names


def generateFea(table, words, glyph_names):
    upper_table = katakanaTable(table)
    def g(char):
        return glyph_names[ord(char)]

    def output(kana):
        return g(kana) if len(kana) == 1 else sequenceGlyphName(kana, glyph_names)

    def toKatakanaGlyph(kana):
        return g(toKatakana(kana))

    def ligaturesOf(table):
        return sorted((entry for entry in table if len(entry[0]) > 1), key=lambda entry: (-len(entry[0]), entry[0]))

    kana_glyphs = [name for cp, name in sorted(glyph_names.items()) if 0x3041 <= cp <= 0x309F or 0x30A1 <= cp <= 0x30FC]
    katakana_glyphs = [name for cp, name in sorted(glyph_names.items()) if 0x30A1 <= cp <= 0x30F6]
    ligatures = ligaturesOf(table)
    singles = [entry for entry in table if len(entry[0]) == 1]
    sequences = sorted({kana for _, kana in table + words if len(kana) > 1})
    upper_ligatures = ligaturesOf(upper_table)
    upper_singles = [entry for entry in upper_table if len(entry[0]) == 1]
    upper_sequences = sorted({kana for _, kana in upper_table if len(kana) > 1})
    uppers = [g(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
    letters = [g(c) for c in "abcdefghijklmnopqrstuvwxyz"] + uppers

    lines = []
    emit = lines.append

    emit("# generated by build.py from data/romaji.tsv and data/words.tsv, do not edit")
    emit("")
    emit("languagesystem DFLT dflt;")
    emit("languagesystem latn dflt;")
    emit("languagesystem kana dflt;")
    emit("")
    emit(f"@KANA = [{' '.join(kana_glyphs)}];")
    emit(f"@KATAKANA = [{' '.join(katakana_glyphs)}];")
    emit(f"@N_KEEPERS = [{' '.join(g(c) for c in N_KEEPERS)}];")
    emit(f"@ANY_N_KEEPERS = [{' '.join(g(c) for c in N_KEEPERS + N_KEEPERS.upper())}];")
    emit(f"@UPPER = [{' '.join(uppers)}];")
    emit(f"@LETTER = [{' '.join(letters)}];")
    emit(f"@LETTER_OR_KATAKANA = [@LETTER @KATAKANA];")
    emit("")

    emit("# K1. an uppercase doubled consonant before another uppercase letter is")
    emit("# small ッ, so the next syllable decides, KITTE is katakana, KiTTe is not")
    emit("lookup upper_sokuon {")
    for consonant in SOKUON_CONSONANTS.upper():
        emit(f"    sub {g(consonant)}' {g(consonant)} @UPPER by {toKatakanaGlyph(SMALL_TSU)};")
    emit(f"    sub {g('T')}' {g('C')} {g('H')} by {toKatakanaGlyph(SMALL_TSU)};")
    emit("} upper_sokuon;")
    emit("")

    emit("# K2. N' is ン")
    emit("lookup upper_n_apostrophe {")
    emit(f"    sub {g('N')} {g(chr(0x27))} by {toKatakanaGlyph(SYLLABIC_N)};")
    emit("} upper_n_apostrophe;")
    emit("")

    emit("# K3. N is ン unless a vowel or y of either case follows, Na stays for な")
    emit("lookup upper_n_syllabic {")
    emit(f"    ignore sub {g('N')}' @ANY_N_KEEPERS;")
    emit(f"    sub {g('N')}' by {toKatakanaGlyph(SYLLABIC_N)};")
    emit("} upper_n_syllabic;")
    emit("")

    emit("# K4. all uppercase syllables, longest first")
    emit("lookup upper_syllables {")
    for romaji, kana in upper_ligatures:
        emit(f"    sub {' '.join(g(c) for c in romaji)} by {output(kana)};")
    emit("} upper_syllables;")
    emit("")

    emit("# K5. expand the katakana temporary glyphs now, so later context")
    emit("# classes only need the real katakana")
    emit("lookup upper_sequences {")
    for kana in upper_sequences:
        emit(f"    sub {sequenceGlyphName(kana, glyph_names)} by {' '.join(g(c) for c in kana)};")
    emit("} upper_sequences;")
    emit("")

    emit("# K6. an uppercase vowel is katakana only next to katakana or another")
    emit("# capital, so a capitalized sentence (Arigatou, Ohayou) stays hiragana")
    emit("lookup upper_vowels_single {")
    for romaji, kana in upper_singles:
        emit(f"    sub {g(romaji)} by {output(kana)};")
    emit("} upper_vowels_single;")
    emit("")
    emit("lookup upper_vowels {")
    vowel_class = " ".join(g(romaji) for romaji, _ in upper_singles)
    emit(f"    sub [@KATAKANA @UPPER] [{vowel_class}]' lookup upper_vowels_single;")
    emit(f"    sub [{vowel_class}]' lookup upper_vowels_single [@KATAKANA @UPPER];")
    emit("} upper_vowels;")
    emit("")

    emit("# 0. fold what is left of A-Z to a-z so every later rule is lowercase only")
    emit("lookup casefold {")
    for upper in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        emit(f"    sub {g(upper)} by {g(upper.lower())};")
    emit("} casefold;")
    emit("")

    emit("# whole word ligatures, only reached through the words lookup")
    emit("lookup word_ligatures {")
    for word, kana in sorted(words, key=lambda entry: (-len(entry[0]), entry[0])):
        emit(f"    sub {' '.join(g(c) for c in word)} by {output(kana)};")
    emit("} word_ligatures;")
    emit("")

    emit("# 1. whole words with no letter or katakana on either side, before any")
    emit("# lowercase letter rule")
    emit("lookup words {")
    for word, _ in words:
        marked = " ".join(f"{g(c)}'" for c in word)
        emit(f"    ignore sub @LETTER_OR_KATAKANA {marked};")
        emit(f"    ignore sub {marked} @LETTER_OR_KATAKANA;")
        # the ligature lookup attaches to the first glyph, where it starts
        first, *rest = [f"{g(c)}'" for c in word]
        emit(f"    sub {first} lookup word_ligatures {' '.join(rest)};")
    emit("} words;")
    emit("")

    emit("# 2. a doubled consonant becomes small tsu plus the consonant, tch too")
    emit("lookup sokuon {")
    for consonant in SOKUON_CONSONANTS:
        emit(f"    sub {g(consonant)}' {g(consonant)} by {g(SMALL_TSU)};")
    emit(f"    sub {g('t')}' {g('c')} {g('h')} by {g(SMALL_TSU)};")
    emit("} sokuon;")
    emit("")

    emit("# 3. n' is always ん, the apostrophe is consumed")
    emit("lookup n_apostrophe {")
    emit(f"    sub {g('n')} {g(chr(0x27))} by {g(SYLLABIC_N)};")
    emit("} n_apostrophe;")
    emit("")

    emit("# 4. n is ん unless a vowel or y follows, end of text included")
    emit("lookup n_syllabic {")
    emit(f"    ignore sub {g('n')}' @N_KEEPERS;")
    emit(f"    sub {g('n')}' by {g(SYLLABIC_N)};")
    emit("} n_syllabic;")
    emit("")

    emit("# 5. syllables, longest first, multi kana outputs go to a temporary glyph")
    emit("lookup syllables {")
    for romaji, kana in ligatures:
        emit(f"    sub {' '.join(g(c) for c in romaji)} by {output(kana)};")
    emit("} syllables;")
    emit("")

    emit("# 6. lone vowels left after the syllables")
    emit("lookup vowels {")
    for romaji, kana in singles:
        emit(f"    sub {g(romaji)} by {output(kana)};")
    emit("} vowels;")
    emit("")

    emit("# 7. expand the temporary glyphs into their kana")
    emit("lookup sequences {")
    for kana in sequences:
        emit(f"    sub {sequenceGlyphName(kana, glyph_names)} by {' '.join(g(c) for c in kana)};")
    emit("} sequences;")
    emit("")

    emit("# 8. a hyphen after kana is the long vowel mark")
    emit("lookup long_vowel {")
    emit(f"    sub @KANA {g('-')}' by {g(LONG_VOWEL)};")
    emit("} long_vowel;")
    emit("")

    emit("# 9. a period or comma right after kana is Japanese punctuation, so")
    emit("# numbers and Latin text keep theirs")
    emit("lookup kana_punctuation {")
    emit(f"    sub @KANA {g('.')}' by {g('。')};")
    emit(f"    sub @KANA {g(',')}' by {g('、')};")
    emit("} kana_punctuation;")
    emit("")

    emit("# ss01: Japanese punctuation everywhere, off by default")
    emit("lookup punctuation {")
    emit(f"    sub {g('.')} by {g('。')};")
    emit(f"    sub {g(',')} by {g('、')};")
    emit("} punctuation;")
    emit("")

    lookup_refs = [
        "upper_sokuon",
        "upper_n_apostrophe",
        "upper_n_syllabic",
        "upper_syllables",
        "upper_sequences",
        "upper_vowels",
        "casefold", "words", "sokuon", "n_apostrophe", "n_syllabic", "syllables", "vowels", "sequences", "long_vowel", "kana_punctuation"]
    # same lookups under both features, a lookup still runs once, so the
    # font still works when a renderer or a user turns only one of them off
    for feature in ["liga", "calt"]:
        emit(f"feature {feature} {{")
        for ref in lookup_refs:
            emit(f"    lookup {ref};")
        emit(f"}} {feature};")
        emit("")

    emit("feature ss01 {")
    emit('    featureNames { name "Japanese punctuation"; };')
    emit("    lookup punctuation;")
    emit("} ss01;")
    emit("")
    return "\n".join(lines)


def generateTs(table, words):
    with open(TS_TEMPLATE, encoding="utf-8") as file:
        source = file.read()

    def fill(source, name, entries):
        empty = f"const {name}: Array<[string, string]> = [];"
        if empty not in source:
            raise SystemExit(f"{name} not found in {os.path.relpath(TS_TEMPLATE, ROOT)}")
        rows = "".join(f"\n\t[{json.dumps(romaji)}, {json.dumps(kana, ensure_ascii=False)}]," for romaji, kana in entries)
        return source.replace(empty, f"const {name}: Array<[string, string]> = [{rows}\n];")

    source = source.replace(
        "// This file is a template. build.py fills the tables marked \"generated\"\n"
        "// from data/romaji.tsv and data/words.tsv and writes dist/kana-liga.ts.\n",
        "// Generated by kana-liga/build.py from kana-liga.ts, data/romaji.tsv\n"
        "// and data/words.tsv, do not edit.\n",
    )
    source = fill(source, "ROMAJI_TABLE", table)
    return fill(source, "WORD_TABLE", words)


def main():
    if not os.path.exists(SOURCE_FONT):
        raise SystemExit("source font missing, run fetch-source.py")
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(DIST_DIR, exist_ok=True)

    table = readRomajiTable(ROMAJI_TABLE)
    words = readRomajiTable(WORD_TABLE)
    source = subsetSource(SOURCE_FONT, CODEPOINTS)
    font, glyph_names = buildFont(source, table + words + katakanaTable(table))

    fea = generateFea(table, words, glyph_names)
    with open(FEA_PATH, "w", encoding="utf-8") as file:
        file.write(fea)
    addOpenTypeFeaturesFromString(font, fea, filename=FEA_PATH)

    with open(TS_PATH, "w", encoding="utf-8") as file:
        file.write(generateTs(table, words))

    font.save(OTF_PATH)
    woff2 = TTFont(OTF_PATH)
    woff2.flavor = "woff2"
    woff2.save(WOFF2_PATH)
    shutil.copy(SOURCE_LICENSE, os.path.join(DIST_DIR, "OFL.txt"))
    shutil.copy(SOURCE_LICENSE, os.path.join(ROOT, "OFL.txt"))

    print(f"{len(table)} romaji entries, {len(words)} words, {len(font.getGlyphOrder())} glyphs")
    for path in [FEA_PATH, OTF_PATH, WOFF2_PATH, TS_PATH]:
        print(f"wrote {os.path.relpath(path, ROOT)} ({os.path.getsize(path)} bytes)")


#
# Code execution
#

if __name__ == "__main__":
    main()
