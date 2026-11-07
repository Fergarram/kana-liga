# TODO

Romaji spellings that don't match how the kana are written, or that the
font renders wrong today.

## Planned

- [ ] **Particle を typed as "o".** "hon o yomu" shows お today. A lone
  "o" between spaces is almost always を, the polite お prefix is written
  attached ("ocha"). Add `o	を` to data/words.tsv, same as "wa".
- [ ] **Hepburn m before b and p.** "shimbun", "sempai", "tempura" show
  しmぶん today. Rule: m followed by b or p becomes ん. Not mm, that stays
  sokuon. Safe, no syllable starts with mb or mp.
- [ ] **nn typed out of IME habit.** "kannji" shows かんんじ today. Rule:
  nn not followed by a vowel or y is a single ん. konna and konnichiwa
  still work since a vowel follows. The test "nn" -> んん becomes ん.

## Maybe

- [ ] **Long vowels as oo / ou / ō.** "tookyoo" gives とおきょお, correct
  is とうきょう. Can't be fixed in general since oo is sometimes really
  おお (ookii). Macrons (tōkyō) don't render at all because ō is not in
  the font. Could add ō ū as おう うう, right most of the time. Only worth
  it if macrons get typed. Plain "tokyo" is unfixable.

## Skipped

- **ぢ/づ in words written with them.** "tsuzuku" gives つずく, correct is
  つづく (also chijimu, hanaji). "du"/"di" already work, a word list
  would only fix the words listed.
- **Particle へ typed as "e".** A lone "e" is also "eh", too ambiguous.
