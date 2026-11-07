#!/usr/bin/env python3
# Shapes romaji with HarfBuzz and checks the glyphs against the expected
# kana, resolved through the font's own cmap. Every case runs with default
# features, with liga off and with calt off, since browsers can drop either.
#
# usage: test.py [font]

import io
import os
import sys

import uharfbuzz as hb
from fontTools.ttLib import TTFont

#
# Constants
#

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FONT = os.path.join(ROOT, "dist", "KanaLiga-Regular.otf")

CASES = [
    ("konnichiwa", "こんにちは"),
    ("kitte", "きって"),
    ("matcha", "まっちゃ"),
    ("kyouto", "きょうと"),
    ("shinbun", "しんぶん"),
    ("senpai", "せんぱい"),
    ("konna", "こんな"),
    ("kan'i", "かんい"),
    ("hon'ya", "ほんや"),
    ("honya", "ほにゃ"),
    ("gakkou", "がっこう"),
    ("tsukue", "つくえ"),
    ("fujisan", "ふじさん"),
    ("si ti tu hu", "し ち つ ふ"),
    ("ra-men", "らーめん"),
    ("watashi wo", "わたし を"),
    # an all uppercase syllable is katakana, mixed case folds to hiragana
    ("Konnichiwa", "こんにちは"),
    ("Watashi Wa", "わたし は"),
    ("KiTTe", "きって"),
    ("TOUKYOU", "トウキョウ"),
    ("ANIME", "アニメ"),
    ("EIGO", "エイゴ"),
    ("KITTE", "キッテ"),
    ("MATCHA", "マッチャ"),
    ("SHINBUN", "シンブン"),
    ("KAN'I", "カンイ"),
    ("KANji", "カンじ"),
    ("Na", "な"),
    ("KO-HI- wo nomu", "コーヒー を のむ"),
    ("FAIRU", "ファイル"),
    ("VAIORIN", "ヴァイオリン"),
    ("PA-THI-.", "パーティー。"),
    ("XTU LTSU XKA", "ッ ッ ヵ"),
    ("KAwa", "カわ"),
    # a lone capital vowel stays hiragana, so a capitalized sentence does
    ("Arigatou", "ありがとう"),
    ("Ohayou", "おはよう"),
    ("A", "あ"),
    ("AI", "アイ"),
    # whole words, only with no letter on either side
    ("watashi wa", "わたし は"),
    ("wa", "は"),
    ("Wa", "は"),
    ("WA", "ワ"),
    ("wawa", "わわ"),
    ("kawa", "かわ"),
    ("niwa", "にわ"),
    ("ni wa", "に は"),
    ("konbanwa", "こんばんは"),
    ("dewa mata", "では また"),
    ("mataha aruiwa moshikuwa sorewa", "または あるいは もしくは それは"),
    ("konnichiwas", "こんにちわs"),
    ("akonnichiwa", "あこんにちわ"),
    ("(wa)", "(は)"),
    # variants and small kana
    ("shi chi tsu fu ji", "し ち つ ふ じ"),
    ("ja zya jya ju zyu jyu jo zyo jyo", "じゃ じゃ じゃ じゅ じゅ じゅ じょ じょ じょ"),
    ("sha sya cha tya cya", "しゃ しゃ ちゃ ちゃ ちゃ"),
    ("di du", "ぢ づ"),
    ("xa la xya xtu xtsu ltu", "ぁ ぁ ゃ っ っ っ"),
    ("ryokan", "りょかん"),
    ("byouin", "びょういん"),
    ("happyaku", "はっぴゃく"),
    ("ressha", "れっしゃ"),
    ("kon", "こん"),
    ("n", "ん"),
    ("nn", "んん"),
    ("ra--men", "らーーめん"),
    # leftovers stay latin
    ("q", "q"),
    ("qa", "qあ"),
    ("k", "k"),
    ("a-b", "あーb"),
    ("123 ok?", "123 おk?"),
    # period and comma after kana are Japanese, elsewhere they stay
    ("desu.", "です。"),
    ("hai, sou desu.", "はい、 そう です。"),
    ("ra-men.", "らーめん。"),
    ("3.14, 2", "3.14, 2"),
    ("ok.", "おk."),
    ("desu..", "です。."),
]

PUNCTUATION_CASES = [
    ("kore wa pen desu.", "これ は ぺん です。"),
    ("konnichiwa, wa.", "こんにちは、 は。"),
    ("hai, sou", "はい、 そう"),
]

FEATURE_SETS = [
    ("default", {}),
    ("liga off", {"liga": False}),
    ("calt off", {"calt": False}),
]

#
# Functions
#

def loadFont(path):
    # HarfBuzz reads sfnt only, so woff2 is decompressed first
    if path.endswith(".woff2"):
        font = TTFont(path)
        font.flavor = None
        data = io.BytesIO()
        font.save(data)
        blob = hb.Blob(data.getvalue())
    else:
        with open(path, "rb") as file:
            blob = hb.Blob(file.read())
    return hb.Font(hb.Face(blob))


def shape(font, text, features):
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(font, buffer, features)
    return [font.glyph_to_string(info.codepoint) for info in buffer.glyph_infos]


def expectedGlyphs(font, text):
    return [font.glyph_to_string(font.get_nominal_glyph(ord(char))) for char in text]


def runCases(font, cases, features, label):
    failures = 0
    for text, expected in cases:
        got = shape(font, text, features)
        want = expectedGlyphs(font, expected)
        if got != want:
            failures += 1
            print(f"FAIL [{label}] {text!r}: want {expected} {want}, got {got}")
    return failures


def main():
    font = loadFont(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FONT)
    failures = 0
    total = 0

    for label, features in FEATURE_SETS:
        failures += runCases(font, CASES, features, label)
        total += len(CASES)

    failures += runCases(font, PUNCTUATION_CASES, {"ss01": True}, "ss01")
    total += len(PUNCTUATION_CASES)

    # without ss01 the punctuation away from kana must survive
    failures += runCases(font, [("3.14", "3.14"), ("q, q.", "q, q.")], {}, "no ss01")
    total += 2

    # with both features off nothing converts
    failures += runCases(font, [("ka", "ka")], {"liga": False, "calt": False}, "both off")
    total += 1

    print(f"{total - failures}/{total} passed")
    sys.exit(1 if failures else 0)


#
# Code execution
#

if __name__ == "__main__":
    main()
