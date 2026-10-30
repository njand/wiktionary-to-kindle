Before marking this release as the latest, load `tr-wiktionary.mobi` on a Kindle (`documents/dictionaries/`) and check it with a Turkish book, then with a book prepared by `prepare-book`. A Kindle folds Turkish letters (ı, İ, I and i weigh the same, as do ş/s, ğ/g, ç/c, ö/o, ü/u) and ignores an apostrophe, so a tap in any case opens the same entry. Words the dictionary does not list whole are split in a prepared book with a hair space (U+200A) between stem and suffixes; a tap on either half opens its own entry.

- [ ] Settings → Dictionaries: under which language the dictionary is listed (it declares `tr`), and whether it opens from a book declared `tr`. Note the language, or that it is missing.
- [ ] The dictionary opens at the "Sources and license" page, titled "Turkish-English Dictionary", with this release's Wiktionary and build dates.
- [ ] `kızı`, `KIZI` and `kizi` open kız; `İyi` and `İYİ` open iyi.
- [ ] `evlerimizden` (a table form) opens ev; `gidip` and `yoktu` open gitmek and yok; `nedeniyle` and `dünyadaki` (generated) open neden and dünya.
- [ ] `yüz` lists yüz (face), yüz (hundred) and yüzmek.
- [ ] `Türkiye'nin` opens Türkiye: note whether the selection takes in the apostrophe (it should; the apostrophe weighs nothing).
- [ ] In the popup for `ev`, the head line reads `ev, evi · noun` with `pl. evler` on a smaller line; `gitmek` reads `gitmek, gider · verb`.

Then the hair space, the check everything in `prepare-book` depends on. Build the test book (35 items: dotted and dotless i, homographs, generated forms, names with apostrophes, split words, and a passage of Ömer Seyfettin's "Aleko" with its split words, once free to break and once in `white-space: nowrap`):

```bash
uv run python scripts/make_device_test.py outputs/KindleDictionary-tr tests/device_words_tr.tsv --lang tr -o outputs/device-test-tr
```

Copy `outputs/device-test-tr/tr-device-test.azw3` to the Kindle's `documents/` folder and check:

- [ ] A long press on either half of a split word (`gözlükçü` + `ler`, `ol` + `ması`) selects that half alone, and the popup lists what "Expect" says: the stem's entry, and for the suffixes their analysis (`-ması`: …ing (verbal noun) + his/her/its), after any word spelled the same.
- [ ] How visible the hair space's gap is inside a word, in Bookerly and one other font, at two sizes.
- [ ] In the first passage, whether any split word breaks across two lines at the hair space; in the second (`nowrap`), that none does.
- [ ] Note the numbers whose popup differs from "Expect" (`predictions.md` has the same list as a table).

Last, a prepared book: run `prepare-book` on a Turkish EPUB without DRM (`prepare-book book.epub --kindling kindling-cli` writes `book-prepared.epub` and `.azw3`), read a few pages, and tap a dozen split words.

Record the device and firmware, and anything that differs, in the release's notes.
