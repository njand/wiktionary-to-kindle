Before marking this release as the latest, load `grc-wiktionary.mobi` on a Kindle (`documents/dictionaries/`) and tap each of these in an Ancient Greek book. A Kindle folds no Greek letter (kindling's measurements), so a tap opens only spellings the dictionary has as labels: without length marks, with a grave for a final acute, and capitalized for headwords and closed-class words. The popup should list every entry a tap reaches, the one the build estimates is most often meant first.

- [ ] Settings → Dictionaries: under which language the dictionary is listed (it declares `grc`), and whether it opens from a book declared `grc`. Note the language, or that it is missing.
- [ ] The dictionary opens at the "Sources and license" page, titled "Ancient Greek-English Dictionary", with this release's Wiktionary and build dates.
- [ ] `καί` and `καὶ` (grave) open καί; `Καὶ` (capital and grave) opens it too.
- [ ] `εἶ` lists εἰμί, then εἶμι, then the letter's name; `θεός` lists θεός, then θεά.
- [ ] `ἀπεκρίθη` opens ἀποκρίνω: a table form Wiktionary writes with a length mark (ῑ).
- [ ] `δʼ` (Perseus's U+02BC) lists δέ (conjunction) and δέ (particle): the selection includes the elision mark or not, and either way it weighs nothing. Note which is selected.
- [ ] `Ἄνδρα` (a capitalized noun form) opens nothing, as predicted; note if it opens ἀνήρ (the device would then fold Greek case).
- [ ] `λύω` written with an oxia (U+1F7B) opens nothing, as predicted; note if it opens λύω (the device would then fold oxia to tonos).
- [ ] In the popup for `λόγος`, the head line reads `λόγος, λόγου ὁ · noun, 2nd decl.`, and the headword is larger than the text after it. In `ἀγαθός`, the headword `ᾰ̓γᾰθός` shows its breves and breathing on the same letter, legibly.
- [ ] Polytonic letters show, in the book and in the popup, with no empty boxes: `ᾄδω`, `ῥήτωρ`, `ᾠδή`, `Ἀχιλλεύς`.

For a wider check, build the test book (32 words: frequent words, capitals, graves and other accents, oxia and decomposed accents, four elision marks, length marks, breathings and iota subscripts), each with the entries its popup should list:

```bash
uv run python scripts/make_device_test.py outputs/KindleDictionary-grc tests/device_words_grc.tsv --lang grc -o outputs/device-test-grc
```

Copy `outputs/device-test-grc/grc-device-test.azw3` to the Kindle's `documents/` folder, tap each bold word, and note the numbers whose popup differs from "Expect" (`predictions.md` has the same list as a table).

Record the device and firmware, and anything that differs, in the release's notes.
