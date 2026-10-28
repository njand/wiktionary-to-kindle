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
- [ ] Alternative-form links never render: Kaikki puts `alt_of` on senses, but the build only looked up a top-level `alt_of` (removed in Stage 5), so `alt_id`/`alt_page` are always `None`.
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

## Stage 3: Coverage — done

- [x] Spelling variants the device does not fold: v→u (`uir`, `uideo`), consonantal i→j (`iam`/`jam`). `utils.lookup_spellings` adds both to every form; j replaces an i before a vowel at the start of a word, between vowels, or after a prefix (`adiuvō`). Cards that differ only by these spellings are merged into one.
- [x] Generated regular comparatives and superlatives (`-ior/-iōris…`, `-issimus/-a/-um`) and the superlative adverb (`-issimē`) from the forms the lemma already tags, tagged `generated` and skipped where Wiktionary has a page. Diminutives only from Wiktionary data (merged from their pages, as before). Indexed as forms of the root entry.
- [x] Declensions of participles that have no page of their own (about 5,100: present `-ns/-ntis`, and `-us/-a/-um` for the others).
- [x] Forms filtered by tag: alternative and Medieval Latin spellings are indexed (`inlābor`, `prelium`), except reconstructions (`*luttra`) and spellings with a page of their own. The `conjugation-3` filter is gone (it only dropped verbs such as `revortō`). Archaic forms were never filtered.
- [x] Headwords with a tie bar (`Orphe͡us`) or another accent that does not compose (`Boō̈tēs`) also get the spelling without it. Abbreviation signs (`aͣ`, `n̄`) are kept: without them the label is another word.
- [x] Found during the full build: Kaikki's `form_of`/`alt_of` targets are often page titles (`iuro`) or macronized differently (`acontīzō`), so about 22,000 pointer pages, mostly single inflected forms and spelling variants (`nārrāvistis`, `jūrō`), stood alone as stub entries. They now merge into the headword with the same letters (the part of speech decides between homographs), so `jūrāvistī`, `iurauisti` and `jurare` all open `iūrō`. A merged page with no forms gives its headword, orphan chains are promoted from the top, and a no-gloss form-of sense counts as a pointer.

How it works: generation and alternative spellings happen in `sort_jsonl`, which sees every headword (`builders/forms.py`, `SORT_VERSION` 5); spelling variants are added where labels are made. The coverage corpus gains `caesar-bg1-u`, Caesar with lowercase v written u.

Measured (2026-10-28, same dump and kindling as the baseline): 54,048 entries (from 76,031; every headword that is no longer an entry still opens one, except 47 multi-word phrases no tap reaches) and 127,708 cards. Labels rose 21% and folded keys 22%, tied keys fell 14%, and the `.mobi` is 73.1 MB (+9%). The build takes 450 s with the re-sort, 310 s without. Corpus: the five Stage 2 sources open 84.8% of tokens (83.6% before): Vulgate 93.3% → 94.6%, Gate to Caesar 56.5% → 58.9%, the rest within 0.1%. The u edition of Caesar opens 97.6%, the same as the v edition. "j for i" misses fell from 380 tokens to 118 (English abbreviations in the glossary, and `Benjamin`). Index order still decides 0.2% of tokens. kindling: 0 hidden labels, and every word in the lookup list opens, including `jam`, `uir`, `uideo`, `Orpheus`, `inlabor` and generated forms such as `ignotiorem`.

Still open, found while doing Stage 3:
- [ ] `Benjamin`: consonantal i after a consonant inside a word (`Beniamīn`) gets no j spelling.
- [ ] u texts print V for capital vocalic u (`Vt`, `Vrbem`); those taps miss.
- [ ] A generated form can be another word's form (`dispēnsō`, dative of the generated participle `dispēnsus` and a verb of its own), which puts both on a card. That is correct, but check how often it happens.

## Stage 4: Entry content — done, device check pending

- [x] Keep the meaning of merged pointer entries as a sub-line of the lemma. A merged page that is a word of its own gets a line by kind (`dim.`, `comp.`, `superl.`, `fem.`, `alt.`, `archaic`, `medieval`, `abbr.`, `syn.`), with the page's own meaning when it adds one: "dim. **puellula**: little girl, lass", "comp. **melior**: better", "alt. **voltus**; **voltum**". Inflections and participles get no line, nor does a comparative or superlative the headword line already names without adding a meaning (`lātior` on lātus).
- [x] Front matter: a first page (`front.xhtml`, guide `copyright-page`) with what the dictionary is, how cards work, attribution to Wiktionary contributors, Kaikki.org and wiktextract, what was changed, the CC BY-SA 4.0 license, the date of the Wiktionary data, the build date and the version. The OPF gains `dc:creator`, `dc:source`, `dc:rights`, `dc:date` and `dc:description`. The downloader keeps the dump's date from Kaikki's `Last-Modified` header in `<file>.date` and carries it to the filtered file; without one, the file's own date is used.
- [x] Popup rendering: kindling strips `class` attributes from entries and compiles only bare-element `font-size` rules, so `.pos` (italic) and `.tag` (small caps) never reached the popup. Parts of speech and labels are now `<i>`, card parses plain text, and the stylesheet keeps only rules for the book view (the `b { font-size: 1.2em }` rule, which kindling would have inlined into every bold word, is gone).

How it works: `sort_jsonl` records each merged page that is a word of its own on the lemma's JSON (`merged_pages`, `builders/related.py`, `SORT_VERSION` 6); `Entry.related` groups them by kind for the template.

Found and fixed while doing Stage 4: following a pointer chain through a form spelled like another lemma (`ferō`, dative of `ferus`) pulled in that lemma's pointers (`lātum`, supine of the verb `ferō`), so `ferus` carried the verb's forms and sat on its cards. Chains now stop at a lemma's headword.

Measured (2026-10-28, same dump and kindling): 54,048 entries (unchanged) and 87,563 cards (−31%). Labels fell 3.2% while folded keys stayed the same (+1), so every spelling still reaches something; the dropped labels and cards were the misattached forms. Tied keys −3.2%, the `.mobi` is 64.5 MB (−12%), 4,881 entries have a sub-line (4,285 `alt.`, 206 `dim.`). Corpus coverage is unchanged (86.4% of tokens open something, 0.2% by index order). kindling: 0 hidden labels, every word in the lookup list opens, no self-check warnings.

Still to check:
- [ ] On a device: the front page, italics in the popup, and how long entries with many `alt.` spellings read.
- [ ] Each card's `<a href>` opens its entry (also listed under Stage 2).
- [ ] The full build's call to kindling failed once on Windows with 0xC0000142 (a DLL initialization failure) after the pages were written; compiling the same OPF by hand worked. A relative `--kindlegen` path also broke the call (kindling runs from the output folder); the CLI now makes an existing path absolute.

## Stage 5: Code health — done

- [x] Restructure into stages: ingest → merge → lexicon model → label resolution → render → compile. `KindleDict` is gone; `pipeline.build_dictionary` runs `ingest.py` (was `downloader.py`), `merge/` (`sort.py` with the external sort and its cache, `pointers.py` with the pointer chains, plus `forms.py` and `related.py`), `models/` (`lexicon.read_entries`), `label_resolver.py`, `render/` (`book.BookWriter`, the card rows, the Jinja renderer) and `compiler.py` (OPF and kindling), and returns a `Build` with the output paths and dates.
- [x] Run `ruff format` over the repo, then add `ruff format --check` to CI (ruff pinned at 0.17.3 in both workflows, so a new release cannot fail a PR).
- [x] Pin the kindling version and verify its checksum in CI; set `KINDLING_STRICT_ENTRIES=1`. CI installs v0.45.6 as `kindling-cli` and checks it against the release's SHA-256.
- [x] CLI cleanup: `--lang` defaults to `la` (it was required with a default), `--kindling` replaces `--kindlegen` (still accepted), every bad argument (no kindling, a missing `--input` or `--kindling` path, `--no-download` without a dump) is a usage error with exit code 2, and `--sort` is hidden. Only kindling is searched for (`kindling-cli` or `kindling` on `PATH`); the Kindle Previewer paths for Amazon's kindlegen are gone.

Found while doing Stage 5:
- [x] The cached sorted dump in `downloads/` had a broken line (line 54,049 started in the middle of an entry), most likely from two sorts writing it at once; the build failed on it. The sort now writes to a file named after its process and renames it when complete.
- The top-level `alt_of` lookup behind the Stage 1 alternative-form bug was dead code and is gone; `Entry` still takes `alt_id`/`alt_page` for when the links are fixed.

- [x] `scripts/check_lookups.py` crashed printing a macronized word to a Windows console; it now writes UTF-8.

Measured (2026-10-28, same dump and kindling): the restructure changes no output. A full build before and after, both sorting the dump again, gives an identical sorted dump, identical XHTML pages and OPF, and a `.mobi` that differs only in the PalmDB header's timestamps (64.5 MB, 54,048 entries). The build passes with `KINDLING_STRICT_ENTRIES=1`, and every word in the lookup list opens. kindling still warns that the book has no NCX table of contents and that `cover.png` is over 127 KB.

## Stage 6: Releases — done, first device check pending

- [x] Coverage numbers in release notes; fail the build on a coverage drop. `quality coverage-diff OLD.json NEW.json --fail-on-drop` compares two coverage reports per source: a source regresses when its share of tokens that open something falls, or its share left to index order rises, by more than 0.5 percentage points, or when kindling reports more words with hidden labels. A source in only one report is listed but not compared (nor is `all` then); a source whose text changed shows its token counts. The weekly build compares its coverage with the latest release's and fails on a regression; a manual run with **Allow a coverage drop** publishes anyway. The release notes add the comparison.
- [x] Spot-check each release on a real device (kindling's simulator is a prediction). Builds are now published as pre-releases, with the checklist in `docs/device-check-la.md` at the end of the notes; after the check, the release is marked as the latest by hand. `gh release download` skips pre-releases, so the next build's index and coverage are compared with the last checked release.
- [x] Optional StarDict export (`--stardict`, `stardict.py`) for KOReader and GoldenDict users. `kindling stardict` writes the bundle from the same OPF; the build then points card links (`0048.xhtml#29169`, dead outside the book) at `bword://lātus²`, the label the entry is stored under, and adds every label's spelling without accents as a synonym unless it is a label of its own (`amavisti` → amō; `latus` stays the card). Released as `la-wiktionary-stardict.zip`.

Measured (2026-10-28, same dump and kindling): a full build with `--stardict` writes XHTML pages and an OPF identical to Stage 5's and a `.mobi` of the same size. The StarDict bundle holds 141,611 words (54,048 entries and 87,563 cards) and 2,388,675 synonyms (1,358,462 from kindling, 1,030,213 unaccented spellings); no page link is left, and the zip is 13.9 MB. The export adds about 15 s. `coverage-diff` against Stage 4 shows no change in any source and passes with `--fail-on-drop`; against the Stage 0 baseline it fails, as it should. Every word in the lookup list opens.

Still to check:
- [ ] The first release goes through the device checklist, which also covers the Stage 0, 2 and 4 device checks.
- [ ] StarDict in KOReader and GoldenDict: card links (`bword://`) open their entries, and an unmacronized tap finds its entry.
- [ ] The workflow changes have not run on GitHub yet (Actions quota).

## Later

Other languages. Hardcoded for Latin today: `name="Latin"` in templates, OPF and HTML headers, `#Latin` in form-of detection, the Latin auxiliary-verb filter.
