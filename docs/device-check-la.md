Before marking this release as the latest, load the `.mobi` on a Kindle (`documents/dictionaries/`, set as the Latin dictionary) and tap each of these in a Latin book. The popup should list every entry a tap reaches, the one spelled like the tap first; for a tap without macrons, the entry the build estimates is most often meant.

- [ ] The dictionary opens at the "Sources and license" page, which gives this release's Wiktionary and build dates.
- [ ] `et` lists et (conj.) and et (adv.), and `quod` lists quod (adv.), quod (conj.), quī and quis: entries with the same spelling are all listed.
- [ ] `non` (unmacronized) lists nōn first, then nōnae; `latus` lists ferō first, then latus (noun), lātus (participle) and lātus (adj.).
- [ ] `Latus` (capitalized) lists the same entries.
- [ ] `lātum` (macronized) lists ferō, lātus (participle) and lātus (adj.), and not latus (noun).
- [ ] `Rōmāni` (partly macronized) lists the same entries as `Romani`.
- [ ] `amāvistī` and `iurauisti` open amō and iūrō.
- [ ] Parts of speech and labels show in italics in the popup.
- [ ] An entry with many `alt.` lines (iūrō, causa) reads well in the popup.
- [ ] `virum​que` with U+200B before `que` selects only `virum` (the enclitic check in Stage 0).

For a wider check, build the test book (87 words: frequent and rare, macronized and not, inflections, spelling variants, homographs, forms of several words, enclitics), each with the entries its popup should list:

```bash
uv run python scripts/make_device_test.py outputs/KindleDictionary-la tests/device_words_la.tsv -o outputs/device-test
```

Copy `outputs/device-test/la-device-test.azw3` to the Kindle's `documents/` folder, tap each bold word, and note the numbers whose popup differs from "Expect" (`predictions.md` has the same list as a table).

Record the device and firmware, and anything that differs, in the release's notes.
