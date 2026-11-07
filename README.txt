KANA LIGA, romaji rendered as kana by the font alone

WHAT THIS IS
	An OpenType font that shows romaji as hiragana using only GSUB
	substitutions. No IME, no JavaScript. The text stays Latin, the
	font draws it as kana: "konnichiwa" displays こんにちわ.
	Syllables typed all uppercase are katakana: "KO-HI-" displays
	コーヒー.

	Outlines come from Noto Sans JP Regular (SIL OFL 1.1), renamed to
	Kana Liga as the OFL requires.

FILES
	fetch-source.py     downloads the pinned source font and license
	data/romaji.tsv     romaji <TAB> kana table, the only place to add
	                    spellings
	data/words.tsv      whole words with a particle は read as wa
	build.py            subsets the source, rebuilds it, generates the
	                    feature file, writes dist/
	test.py             shapes test strings with HarfBuzz
	build/kana-liga.fea generated feature file, for inspection only
	kana-liga.ts        template of romajiToKana(), the same lookups
	                    replayed in JS, build.py fills in the tables
	dist/               KanaLiga-Regular.otf, KanaLiga-Regular.woff2,
	                    kana-liga.ts, OFL.txt. Copy kana-liga.ts into
	                    the site's modules to publish it.
	OFL.txt             license of the source and of this font

BUILD
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/python fetch-source.py
	.venv/bin/python build.py
	.venv/bin/python test.py
	.venv/bin/python test.py dist/KanaLiga-Regular.woff2

	If the venv has no pip (Debian without python3-venv), create it
	with --without-pip and run get-pip.py from bootstrap.pypa.io with
	the venv's python.

SOURCE
	notofonts/noto-cjk, tag Sans2.004,
	Sans/SubsetOTF/JP/NotoSansJP-Regular.otf

	That file is CID-keyed CFF, so its glyph names (cid01461) mean
	nothing. build.py never uses names from it. It finds every glyph
	through the cmap, subsets with fontTools.subset (dropping its GSUB,
	GPOS and BASE), then redraws the glyphs into a new name-keyed CFF
	font with FontBuilder, naming them a, hyphen, uni3042 and so on.

	Kept: basic Latin U+0020 to U+007E, hiragana U+3041 to U+3096 and
	U+3099 to U+309F, katakana U+30A1 to U+30F6, ー U+30FC, 。、「」.

LOOKUP ORDER
	All lookups below are registered under both liga and calt. A lookup
	shared by two features still runs only once, and the tests check
	that either feature alone is enough.

	K1 upper_sokuon  chain sub, an uppercase doubled consonant before
	                 another uppercase letter gives ッ (KKA -> ッKA),
	                 TCH gives ッ
	K2 upper_n_apostrophe
	                 ligature, N' -> ン
	K3 upper_n_syllabic
	                 N -> ン unless a vowel or y of either case follows,
	                 so Na is left for な
	K4 upper_syllables
	                 the table as uppercase romaji to katakana, longest
	                 first
	K5 upper_sequences
	                 expands the katakana temporary glyphs right away,
	                 so the classes after this only need real katakana
	K6 upper_vowels  chain sub, an uppercase vowel next to katakana or
	                 another capital is katakana. A lone capital vowel
	                 is not, so Arigatou and Ohayou stay hiragana.
	0  casefold      single sub, what is left of A-Z to a-z
	1  words         chain sub, a word from data/words.tsv with no
	                 letter or katakana on either side becomes a ligature
	                 (wa -> は, konnichiwa -> こんにちは). It runs before
	                 the letter rules, so they never see these words.
	2  sokuon        chain sub, a doubled consonant other than n gives っ
	                 plus the consonant (kk -> っk), and t before ch
	                 gives っ (tch -> っch)
	3  n_apostrophe  ligature, n' -> ん, the apostrophe is consumed
	4  n_syllabic    ignore sub n' [a e i o u y]; sub n' -> ん
	                 This also covers end of word and end of text. nn is
	                 not special: the first n is followed by n so it
	                 becomes ん, and the second stays for the next
	                 syllable (konnichiwa, konna).
	5  syllables     ligatures from the table, longest first
	6  vowels        single sub for a i u e o left alone
	7  sequences     multiple sub, temporary glyph -> two real kana
	8  long_vowel    chain sub, hyphen after any kana -> ー, katakana
	                 included (KO-HI- -> コーヒー)
	9  kana_punctuation
	                 chain sub, . and , right after any kana -> 。 and 、
	                 (desu. -> です。), so numbers (3.14) and Latin
	                 text keep theirs

	ss01 (off by default): every . -> 。 and , -> 、

YOON
	A ligature can output only one glyph, so a two kana output like
	kya -> きゃ is a ligature to an empty temporary glyph
	(seq.uni304D_uni3083) followed by a multiple substitution (GSUB
	type 2) into き and ゃ. Type 2 works in HarfBuzz (Chrome, Firefox,
	Android, Linux), CoreText and DirectWrite. The output is the real
	kana glyphs, so metrics, kerning and tests behave like ordinary
	text. The other option, a composite glyph per pair, does not exist
	in CFF and would mean around 100 double width copies of outlines.

ROMANIZATION
	Hepburn, Kunrei and wapuro spellings: shi/si, chi/ti, tsu/tu,
	fu/hu, ji/zi, ja/zya/jya, sha/sya, cha/tya/cya, di ぢ, du づ,
	wo を, every yoon, fa fi fe fo, va vi vu ve vo, thi dhi, and small
	kana with an x or l prefix (xa la ぁ, xya ゃ, xtu xtsu ltu っ, xwa
	ゎ, xka ゕ, xke ゖ).

KATAKANA
	A syllable is katakana when every letter of it is uppercase. KA is
	カ, Ka and kA fold to lowercase and are か. Every table row works
	uppercase, with the same rules for sokuon, n and ー:

		KITTE キッテ    KiTTe きって    SHINBUN シンブン    KAN'I カンイ
		FAIRU ファイル  PA-THI- パーティー  KANji カンじ

	The small ッ before a doubled consonant follows the syllable after
	it. A capital vowel on its own is katakana only next to katakana
	or another capital, so a sentence that starts with a capital
	(Arigatou, Ohayou, A) stays hiragana while ANIME and AI are アニメ
	and アイ. Use the katakana spellings for katakana sounds: THI is
	ティ, TI is チ.

	To add a spelling, add a line to data/romaji.tsv and rebuild. A
	multi kana output gets its temporary glyph automatically.

KNOWN LIMITATIONS
	Copy and paste gives back the original romaji, since the text never
	changes. Pages can convert on copy with romajiToKana() from
	dist/kana-liga.ts.
	"wa" on its own between spaces or punctuation is the particle は,
	so the rare sentence final わ ("sou da wa") comes out as は too.
	Inside a word wa is always わ, except for the few set phrases in
	data/words.tsv. Ambiguous words like niwa (には or 庭) and towa
	are left out, write "ni wa" to get the particle. The particle へ
	needs "he", a lone "e" stays え.
	No kanji.
	No Latin capitals. Capitals that make no katakana syllable are
	folded to lowercase, so they display in lowercase.
	Caps lock types katakana, and so does English in capitals that
	happens to spell syllables (OK is オk).
	Letters that make no syllable stay as lowercase Latin (q, a stray
	k).
	The glyphs are redrawn without hints and the source GPOS is
	dropped, so there is no Latin kerning and no vertical metrics
	(vhea/vmtx).
	Line breaking and text selection treat the text as Latin words.
	Browsers can break or select inside a ligature and split a
	syllable.
	Any letter-spacing other than 0 makes Chrome turn off liga and calt
	together, so the romaji stays Latin.
	Chrome reshapes only the edited part of editable text, so a
	syllable typed letter by letter stays Latin (わたsひ) until the
	text is reshaped. Pasted text is fine. Editors work around it by
	changing font-feature-settings on every input (forceReshape in
	fernando.computer's journal).
	Shaping only happens inside one run. Changing font, style or color
	partway through a syllable stops the ligature from forming.
