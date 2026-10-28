Before marking this release as the latest, load the `.mobi` on a Kindle (`documents/dictionaries/`, set as the Latin dictionary) and tap each of these in a Latin book. kindling's `lookup` predicts the result on a Paperwhite 5; this checks the real device.

- [ ] The dictionary opens at the "Sources and license" page, which gives this release's Wiktionary and build dates.
- [ ] `latus` (unmacronized) opens the card listing ferō, lātus (verb), lātus (adj.) and latus (noun); each row's link opens that entry.
- [ ] `Latus` (capitalized) opens the same card.
- [ ] `lātum` (macronized) opens the card for its three owners, not one of them at random.
- [ ] `Rōmāni` (partly macronized) opens the card kindling predicts for `Romani`.
- [ ] `amāvistī` and `iurauisti` open amō and iūrō.
- [ ] Parts of speech and labels show in italics in the popup.
- [ ] An entry with many `alt.` lines (iūrō, causa) reads well in the popup.
- [ ] `virum​que` with U+200B before `que` selects only `virum` (the enclitic check in Stage 0).

For a wider check, build the test book (87 words: frequent and rare, macronized and not, inflections, spelling variants, homographs, forms of several words, enclitics), each with kindling's prediction:

```bash
uv run python scripts/make_device_test.py outputs/KindleDictionary-la tests/device_words_la.tsv -o outputs/device-test
```

Copy `outputs/device-test/la-device-test.azw3` to the Kindle's `documents/` folder, tap each bold word, and note the numbers whose popup differs from "Expect" (`predictions.md` has the same list as a table).

Record the device and firmware, and anything that differs, in the release's notes.
