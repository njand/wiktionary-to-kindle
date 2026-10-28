# Roadmap

Development plan for the Latin dictionary, with the decisions and research it rests on.
Update this file as stages finish. Scope is Latin only; other languages come later.

## Decisions (2026-10-27)

| Question | Decision |
| --- | --- |
| Compiler | **kindling only.** Drop Amazon kindlegen support, including the 200-form entry splitting (its 255-form limit is kindlegen-only; kindling has no per-entry limit). |
| Homographs (latus / lātus) | **Keep entries separate.** A tap on a macronized word ("lātum") should open only the matching entry. Where a choice is unavoidable, prefer something the reader can swipe or jump between over one long merged entry where the boundary between entries is easy to miss. See Stage 2. |
| Enclitics (-que, -ne, -ve) | **Not indexed.** Enclitics will be pre-segmented in the e-books with an invisible space instead. Verify on a device first (Stage 0). |
| Examples pipeline | **Remove it.** The CLI never enables `link_examples`. |

## How Kindle lookup works (what the design must respect)

Amazon documents almost none of this. Sources: the [kindling README](https://github.com/ciscoriordan/kindling) (measured on Kindle 4, Paperwhite 4 and Paperwhite 5), [KDP: Creating Dictionaries](https://kdp.amazon.com/en_US/help/topic/G2HXJS944GL88DNV).

- A tapped word reaches every label with the same weights. For Latin letters, case and accents (macrons included) do not count; ß/æ/œ count as ss/ae/oe; punctuation weighs nothing; a separate combining mark (the breve in ā̆) counts as itself. `kindle_fold()` in `utils.py` approximates this.
- Of the labels reached, one opens: the one spelled exactly like the tapped word; else the first equal to it ignoring case (accents still count); else, apart from some prefix rules, the first in stored index order. Nothing matches by prefix.
- So ties are decided by index order, which explains the "unpredictable" capital-letter and macron behavior. The current standalone inflection cards compete with the lemma's identical labels instead of replacing them.
- The device folds macrons and case itself, so generating unmacronized/lowercase variants adds nothing for matching. Their only effect is to create exact-spelling ties.
- `kindling-cli lookup <dict.mobi> <word>` predicts what a Paperwhite 5 opens, exits 1 on a miss, and reports ties and labels the index order hides.
- KDP lists a copyright page as required content; Wiktionary text is CC BY-SA, so an attribution and license page is needed.
- Wiktionary's Latin conventions: page titles without macrons, headwords with macrons, ā̆ for disputed length, v for consonantal u, no j, no æ/œ ligatures in headwords. Kaikki `form_of`/`alt_of` targets keep macrons. Kaikki's per-language downloads are deprecated; the raw dump is the source.

## Stage 0: Measure — done (PR #1)

- `python -m wiktionary_to_kindle.quality stats|diff|coverage|sample` (see README, "Measuring lookup quality").
- Corpus: `corpus/la.tsv`. Lookup assertions: `tests/lookup_words_la.txt` via `scripts/check_lookups.py`.
- The sorted dump is cached (`SORT_VERSION` in `kindle_dict.py`; bump it when sort output changes).

Still to do:
- [x] **Local baseline** (2026-10-28, dump of 2026-10-25, kindling v0.45.6). Stage 0 (`2123d0a`): 80,230 entries, 2,988,049 labels, 310,573 tied folded keys, 98.0 MB `.mobi`, built in 388 s. Corpus: 83.6% of tokens open something, 42.0% by index order. Every word in the lookup list opens. Measurements are kept outside the repo, in `outputs/measure/` (gitignored).
- [ ] **Check enclitic pre-segmentation on a device.** Insert U+200B between a word and its enclitic in a test book and confirm the Kindle selects only the word when tapped. If the reader does not treat it as a word break, the invisible character weighs nothing and the tap becomes `virumque` again (a miss).
- [ ] **Check whether the Kindle popup can show several entries** (the swipe between results). Find what triggers it; it changes the Stage 2 design.

## Stage 1: Quick correctness fixes (each with a test) — done

- [x] Descendants: filter by `lang` (name), not `lang_code`; show the language name.
- [x] Move templates into the package (`importlib.resources`) so an installed wheel works.
- [x] `format_etymology`: rewrite with `str.find`; it drops trailing characters and misses overlapping matches.
- [x] `Header.split_components`: headwords with two or more ā̆ vowels are cut short.
- [x] `MorphTag`: `sup` means both supine and superlative (superlative is now `superl`); `__lt__` returns `None`. `Inflection.__lt__` raises `TypeError` with mixed tag/no-tag inflections.
- [x] Do not index entries that render no senses.
- [x] Downloader: write to a temp name and rename; no `shell=True`; honor `--input` without `--no-download`.
- [x] `SensesBlock.lookup_sense` mutates the caller's list; `sanitize_xhtml` misses `&`; header prefixes are escaped twice.
- [x] Remove the examples pipeline (decision above) and other dead code: `Descendant`, `.id` on headers and split entries, `Example.bold_word`, `MACRONIZED_VOWELS`, unused parameters, the per-entry bold regex.

Found while doing Stage 1, not yet fixed:
- [ ] Alternative-form links never render: `build_dictionary` looks up a top-level `alt_of`, but Kaikki puts `alt_of` on senses, so `alt_id`/`alt_page` are always `None`.
- [ ] `Entry.get_senses_blocks` adds each sense to the most recently created block instead of block `head_nr`, so a first-headword sense listed after a second-headword one lands under the second.

## Stage 2: Deterministic lookups, entries kept separate — done, device check pending

Goal: every tap opens one predictable thing, and a macronized tap opens the matching entry.

- [x] Build a label index over the whole dictionary: exact spelling → owners, and folded key → owners.
- [x] **One owner per exact spelling.** A macronized label such as `lātum` stays on its own entry when only one entry has it, so a macronized tap goes straight there.
- [x] **Unmacronized spellings of ambiguous keys go to a disambiguation card.** If a folded key (e.g. `latum`) reaches several entries, an unmacronized label owned by one short card lists each candidate (headword, part of speech, parse, first gloss, link). Remove that spelling from the entries themselves. A tap in an unmacronized text then lands on the card instead of whatever index order picks.
- [x] Spellings shared exactly by several entries (same macrons, different lemmas) also go to a card.
- [x] Stop generating unmacronized and case variants except where a card needs the label.
- [x] Drop entry splitting (kindling only).
- [ ] Revisit if the device can show multiple entries natively (Stage 0 check).
- Done when: coverage shows 0 ambiguous words, kindling reports no hidden labels, and the capital-letter and macron probe words open the same entry every time.

How it works (`builders/label_resolver.py`): the build reads the dump twice. The first pass collects every entry's labels; the resolver groups labels that differ only by accents, case or æ/œ and creates cards; the second pass renders entries with the labels left to them, then the cards (`card-NNNN.xhtml`, ids `card_N`). Labels differing only by punctuation (`ad`, `a.d.`) make no card: the entry spelled like the tap gets the plain spelling (`non` on nōn), and a card takes the bare spelling only when every label has punctuation (`M.`, `M'`). Card rows are ordered by how much Wiktionary says about each entry (JSON size without the inflection table), proper names last. An entry whose headword a card takes is indexed as `latus¹`, `latus²` (its place on the card); the superscript has its own weight, so no tap reaches it.

Measured (2026-10-28, same dump and kindling as the baseline): 76,031 entries (the 4,522 copies made by splitting are gone) and 140,266 cards, 86% of them with two rows. Labels fell 57% (no unmacronized variants) while folded keys rose 2.6%, so no tappable spelling was lost. Tied keys fell 92%, the `.mobi` is 67.0 MB, and the build takes 196 s with a 616 MB peak. Corpus: 83.6% of tokens still open something; tokens left to index order went from 42.0% to 0.2%, all in the macronized edition, and kindling resolves those to the card's plain label. kindling: 0 hidden labels, and every word in the lookup list opens.

Trade-off: in unmacronized texts about half of the taps that open something land on a card (`et`, `est`, `cum`, `quod`, `te`) instead of an entry. The card shows each candidate's first gloss, so it is often enough on its own.

Still to check:
- [x] Full build against the Stage 0 baseline (above).
- [x] kindling: labels like `latus¹` compile and pass its checks.
- [ ] Each card's `<a href>` opens its entry (kindling does not simulate following links).
- [ ] On a device: cards are readable in the popup, a capitalized tap (`Latus`) opens the card, and a partially macronized tap (`Rōmāni`) opens the card as kindling predicts.

## Stage 3: Coverage

- [ ] Spelling variants the device does not fold: v→u (`uir`, `uideo`), consonantal i→j (`iam`/`jam`).
- [ ] Generated regular comparatives and superlatives (`-ior/-iōris…`, `-issimus/-a/-um`) and adverbs from the forms the lemma already tags, marked as generated and skipped where Wiktionary has them. Diminutives only from Wiktionary data. Indexed as forms linking to the root entry.
- [ ] Declensions of participles that have no page of their own.
- [ ] Reconsider forms filtered by tag (`alternative`, archaic, `Medieval-Latin`).
- [ ] Headwords with a tie bar (`Orphe͡us`) keep a combining mark that weighs as itself, so a tap on `Orpheus` cannot reach them; add the spelling without it.

## Stage 4: Entry content

- [ ] Keep the meaning of merged pointer entries as a sub-line of the lemma ("dim. puellula — little girl", "comp. lātior").
- [ ] Front matter: copyright, license and attribution page, dump date, version.
- [ ] Check how entries render in the lookup popup (no stylesheet; kindling compiles some CSS into inline tags).

## Stage 5: Code health

- [ ] Restructure into stages: ingest → merge → lexicon model → label resolution → render → compile (fits with Stage 2).
- [ ] Run `ruff format` over the repo, then add `ruff format --check` to CI.
- [ ] Pin the kindling version and verify its checksum in CI; set `KINDLING_STRICT_ENTRIES=1`.
- [ ] CLI cleanup: `--lang` default, consistent errors.

## Stage 6: Releases

- [ ] Coverage numbers in release notes; fail the build on a coverage drop.
- [ ] Spot-check each release on a real device (kindling's simulator is a prediction).
- [ ] Optional StarDict export (`kindling stardict`) for KOReader and GoldenDict users.

## Later

Other languages. Hardcoded for Latin today: `name="Latin"` in templates, OPF and HTML headers, `#Latin` in form-of detection, the Latin auxiliary-verb filter.
