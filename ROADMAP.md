# Roadmap

Development plan for the Latin dictionary and the languages after it (Ancient Greek, then Turkish), with the decisions and research it rests on.
Update this file as stages finish. Stages 0–6 are Latin; Stage 7 makes the build language-neutral; Stages 8–11 are Ancient Greek; Stage 12 outlines Turkish.

## Decisions (2026-10-27)

| Question | Decision |
| --- | --- |
| Compiler | **kindling only.** Drop Amazon kindlegen support, including the 200-form entry splitting (its 255-form limit is kindlegen-only; kindling has no per-entry limit). |
| Homographs (latus / lātus) | **Keep entries separate.** A tap on a macronized word ("lātum") should open only the matching entry. Where a choice is unavoidable, prefer something the reader can swipe or jump between over one long merged entry where the boundary between entries is easy to miss. See Stage 2. |
| Enclitics (-que, -ne, -ve) | **Not indexed.** Enclitics will be pre-segmented in the e-books with an invisible space instead. Verify on a device first (Stage 0). |
| Examples pipeline | **Remove it.** The CLI never enables `link_examples`. |
| Disambiguation cards (2026-10-28) | **Drop them.** The device popup lists every entry a tap reaches (see Stage 6, found on the device), and links do not work in the popup, so a card only added a step. Each entry keeps all its own spellings. |
| Next languages (2026-10-29) | **Ancient Greek, then Turkish.** Greek is closest to Latin: an inflected classical language whose Wiktionary tables list nearly every form, so most of the Latin pipeline carries over. Turkish needs morphology the tables cannot list (Stage 12). |
| Preparing books (2026-10-29) | **Allowed.** Where the dictionary alone cannot reach a word, a `prepare-book` command may normalize or segment the e-book (Unicode form and elision marks for Greek, an invisible break between stem and suffixes for Turkish, enclitics for Latin). The dictionary comes first: a book change is only for what labels cannot do at a reasonable size. |

## How Kindle lookup works (what the design must respect)

Amazon documents almost none of this. Sources: the [kindling README](https://github.com/ciscoriordan/kindling) (measured on Kindle 4, Paperwhite 4 and Paperwhite 5), [KDP: Creating Dictionaries](https://kdp.amazon.com/en_US/help/topic/G2HXJS944GL88DNV).

- A tapped word reaches every label with the same weights. For Latin letters, case and accents (macrons included) do not count; ß/æ/œ count as ss/ae/oe; punctuation weighs nothing; a separate combining mark (the breve in ā̆) counts as itself. `kindle_fold()` in `utils.py` approximates this.
- Of the labels reached, kindling predicts one opens: the one spelled exactly like the tapped word; else the first equal to it ignoring case (accents still count); else, apart from some prefix rules, the first in stored index order. Nothing matches by prefix.
- On a device (2026-10-28) the popup lists **every** entry reached, that one first, and the reader swipes to the rest, which follow in the order kindling's index search returns their labels (2026-10-29: `non` listed nōnae, labelled `Non.`, before nōn, as `kindling-cli lookup` predicts). Links do not work in the popup.
- kindling (v0.45.6) stores **one index record per label string**: when several entries have the same label (`et` conjunction and adverb), only one of them is reached and the popup lists only that one. The build gives the others a soft hyphen (which weighs nothing) after the first letter, one more per entry (`render/shared_labels.py`).
- The device folds macrons and case itself, so generating unmacronized/lowercase variants adds nothing for matching. Their only effect is to create exact-spelling ties, which decide which entry the popup lists first: since 2026-10-29 the likeliest entry of each ambiguous spelling gets the unmacronized one for that reason (`render/popup_order.py`).
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
- [x] **Check whether the Kindle popup can show several entries** (the swipe between results). It always does: every entry a tap reaches is listed (Stage 6 device test). Cards were dropped for it.

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

## Stage 2: Deterministic lookups, entries kept separate — done, then superseded

Superseded on 2026-10-28: the device lists every entry a tap reaches, so the cards were dropped (see Stage 6, "Found on the device"). What follows describes the card design as it was.

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
- [ ] The test book (`scripts/make_device_test.py`, words in `tests/device_words_la.tsv`) is checked on a device. Building it found that no entry has a label with a breve (`ā̆`), so a text that prints one misses; check how often texts do.
- [ ] StarDict in KOReader and GoldenDict: card links (`bword://`) open their entries, and an unmacronized tap finds its entry.
- [ ] The workflow changes have not run on GitHub yet (Actions quota).

Found on the device with the test book (2026-10-28):
- [x] **The popup shows every entry a tap reaches**, not one: a result for each entry or card with a label of the same weights, the one spelled like the tap first, the rest swiped through. kindling's `lookup` predicts only the first. So `fēmina` showed three cards (`fēmina`, `femina`, `fēminā`), and `est` the card and `edō` (which kept `ēst`). **Links do not work in the popup**, so a card was only an overview. The cards are dropped: `label_resolver.py`, the card pages and the numbered headwords (`latus¹`) are gone, every entry is indexed by all its own spellings, and the build reads the dump once. The coverage gate no longer fails on index order or on kindling's hidden labels, which now only decide which entry the popup shows first. StarDict adds an unaccented synonym even where another word has that spelling, so `latus` finds lātus too. The device test book lists every entry each tap should show.
- [x] Descendants of one language share a line (**Spanish:** llave, clave), without exact repeats.
- [x] kindling drops a space that stands alone between two inline elements (`</a> <i>` compiles to `</a><i>`), so card rows read `ferōverb` and sub-lines `dim.frīgidulus`. The renderer writes a no-break space there.
- [x] A symbol weighs nothing: forms like `☿ōs` and `♃vis` (written with a planet's sign) were reached by `os` and `vis`. Forms with a symbol are no longer indexed, and `kindle_fold` drops symbols.
- [x] A parent sense that is only a qualifier (omnis: "(as adjective)") lost its sub-senses: Kaikki leaves it out of `glosses` but not `raw_glosses`, and the alignment paired the wrong ones.
- [x] A descendant reached through several branches was listed once per branch (French `à l'onni` three times under omnis).

Second test book (2026-10-28, the build without cards): 38 of 87 popups listed fewer entries than predicted. Every one fits a single rule: of the entries sharing an exact label, one is listed. `et` showed only the adverb, `quod` only quod (conj.) and none of quī/quis, `lātus` only lātus (adj.) and latus, `legere` only legō (lēgō's `lēgēre` was taken by legō). `kindling dump` confirms the index holds one record per spelling. Which one survives: the last entry whose headword it is, else the first that has it as a form.
- [x] Shared labels: each entry after the first gets soft hyphens inside its label (`et` stays on the conjunction, the adverb gets `e`, soft hyphen, `t`), which weigh nothing, so kindling keeps a record per entry. Headwords keep the plain spelling before forms do, so a tap spelled like it opens a headword first. Inside the word because kindling stores a label with a soft hyphen at either end ahead of the plain one (the Kindle drops it from a tapped word), so an inexact tap would open it first; a one-letter label gets them after. StarDict keeps every entry of a word, so the export takes them out again.
- [x] Participles and gerunds showed as "verb" (`amāns`): Kaikki files them under `verb`; the part of speech now comes from the head template (`la-part`, `la-gerund`).
- [x] Check the soft-hyphen labels on the device with the rebuilt test book. Third test book (2026-10-29): every popup listed the predicted entries, but often in another order. The book predicted the order of the pages; it now predicts the order of kindling's index search (`non`: nōnae, then nōn).
- [x] `erīs` was an entry of its own ("dative/ablative plural of erus and era"): Kaikki names both lemmas in one `form_of` target, which matches no headword, so the page was promoted as an orphan. A target with spaces now resolves to the first linked word it starts with (`erus`, `pār` for "pār m or f"), 584 senses.
- [x] An unmacronized tap listed entries in kindling's label order, so the most common word was often not first (`non`: nōnae before nōn; `more`: mōrus before mōs). With no frequency data, the build estimates it (`render/popup_order.py`): how much Wiktionary says about the entry (the JSON without the inflection table), doubled for a headword, a tenth for a proper name or an alternative spelling. The likeliest entry of each spelling several entries share without accents gets that spelling as a label, and keeps a shared label plain (`shared_labels.py`, which put headwords first before).
- [x] Fourth test book (2026-10-29): every popup matched its prediction. Found there:
  - `ad` listed annō and ante: the two-lemma fix above also split phrases ("initialism of ante diem"). Only a target whose first word is followed by "and", "or" or a gender (m, f, n) is split now.
  - `se` listed suī, then seipse, sī and sē: only the first entry followed the estimate. kindling orders the labels a tap reaches by a fixed chain (`mobi.rs`: labels the Kindle rewrites, such as `se-`, first; then fewer accents, fewer capitals, fewer soft hyphens). Every entry of an ambiguous spelling now gets that spelling with as many soft hyphens as its rank, and its punctuated or plain labels of the spelling are dropped, so the whole popup follows the estimate.
  - Gothic (and cuneiform, Avestan, Linear B, ... : any script outside the Basic Multilingual Plane, and Runic) shows as boxes: no Kindle font has it. Such a word is replaced by the transliteration Wiktionary gives with it ("Gothic 𐌰𐍄𐌹𐍃𐌺 (atisk)" → "Gothic atisk"); 111 without one are left.
  - 14,607 etymologies began with Wiktionary's etymology tree flattened into a list of ancestors ("Etymology tree Proto-Indo-European *h₃reǵ- …"). The tree is cut up to the line naming the word itself; 19 where that line is missing are left.
- [x] A more compact entry, so the popup's first screen shows more of the meaning: the headword, its forms and declension (`3rd decl.`, `1st conj.`) and the part of speech share one line; alternative forms, diminutives and abbreviations share one line; *Etym.* and *Desc.* head their paragraphs instead of headings, and descendants share one line with short language names (`It. re; Fr. roi`).
- [x] Dictionary-style layout. The popup applies no CSS and kindling strips `style` attributes, but `<font size="±N">` renders in it (kindling `dict_css.rs`, checked on a Paperwhite by kindling's author), so:
  - The headword is one size larger, followed by its principal parts without labels and its gender (`rēx, rēgis m. · noun, 3rd decl.`, `amō, amāre, amāvī, amātum · verb, 1st conj.`); other forms (`fem. rēgīna`, `comp. lātior`) go on a smaller line under it (`render/headline.py`). A head line of another shape is only shortened.
  - Labels before a sense are shortened and lose their parentheses (`trans.`, `fig.`, `Med. Lat.`).
  - **Etymology.** and **Descendants.** are bold run-in labels; their text is one size smaller and grey (`<font color>`, not yet checked on a device). Descendant languages are bold (`It. re, rege · Fr. roi`).
  - In etymologies only the cited word is italic (Proto-Italic *\*rēks*), and Proto-Indo-European is PIE. Etymologies are given whole: they close the entry, after the meanings, so their length costs no first-screen space. (Shortening the 5,900 over 300 characters to their chain of ancestors was tried and dropped on 2026-10-29: it reduced Caesar's competing theories to "Origin unknown; perhaps from Punic".) Their paragraphs and list items run on.
- [ ] Check the compact layout on the device.
- [ ] Check the predicted order on the device with the fourth test book.
- [ ] `vēnit` listed veniō before vēneō, although the index stores `vēnit` for vēneō and veniō is reached by `venit` (kindling predicts vēneō first). Every other popup put the entry spelled like the tap first.

## How Kindle lookup works for Greek (what Stages 8–11 must respect)

From kindling's README and source (checked 2026-10-29), not yet measured on a device by this project:

- **The device folds nothing in Greek.** Latin letters weigh as their lowercase base letter, but "Greek, Cyrillic, Armenian and Hebrew letters, the combining marks" weigh as themselves, "so its case and accents count" (`Κάτι` does not find `κάτι`). This is the opposite of Latin: there, extra spellings only decide the popup order; in Greek, every spelling a text prints must be a label or the tap misses.
- A Greek book ignores Greek case only when choosing among labels that already have the same weights, so it does not rescue a capitalized tap.
- Code points count, not canonical equivalence: oxia `ά` (U+1F71) and tonos `ά` (U+03AC) are different characters to the device, and "a decomposed `é` is not a precomposed one". `kindle_fold` normalizes to NFC first, which is right for Latin texts and wrong here.
- Punctuation weighs nothing: the right single quotation mark (U+2019) and the modifier apostrophe (U+02BC, in the spacing-modifier block) used for elision drop out of a tapped word; the Greek koronis/psili `᾽` (U+1FBD, Greek Extended) does not.
- Greek dictionaries get kindlegen's Greek ORDT/SPL blob by default, which covers Greek Extended (U+1F00–U+1FFF). The language does not change the weights; the Kindle 4 looks a word up in the dictionary whose language matches the book's. kindling maps `grc` to its own LCID.
- Lemma, the Modern Greek dictionary kindling's author builds, adds case variants (`φας`/`Φας`) and corpus-attested polytonic forms (from Wikisource) to its 31K headwords and 568K forms: the same approach this plan takes.
- Kaikki's Ancient Greek data (2026-10-29, λύω): the headword and the table forms carry macrons and breves (`λῡ̆́ω`, `λῡ́ουσῐν`), the page title does not (`λύω`). Participles are listed in the nominative only (`λῡ́ων`, `λῡ́ουσᾰ`, `λῦον`). Dialects (Epic, Ionic, ...) are named by `table-tags` rows that head each table, not on each form. A full verb's forms run to hundreds; the page for λύω is 640K characters.

## Stage 7: Language profiles — done

Goal: one place per language for everything Latin-specific, so `--lang grc` builds through the same pipeline.

- [x] `wiktionary_to_kindle/languages/`: a `Language` profile per language (`la.py`, `grc.py`), chosen by `--lang` (`choices` are the registered codes) and passed to every stage: `merge_dump`, `read_entries` and `Entry`, `BookWriter`, `write_opf`, coverage and `quality sample`. A profile holds:
  - Wiktionary's code and name: the `idx:entry` name and `DefaultLookupIndex` (`index_name`: `Latin`, `Greek`), the front page and OPF title, `DictionaryInLanguage`, the OPF identifier and the StarDict description.
  - The section anchor form-of links end with (`#Latin`, `#Ancient_Greek`), from the name.
  - `letters`, what a form-of target is matched by when no headword is spelled like it (`rekey_plain_roots`): Latin strips every accent (`normalize`); Greek drops only macrons and breves (`grc.strip_length`), since accents and breathings belong to the spelling (ὡς, ὥς).
  - `lookup_spellings`: Latin's (moved from `utils.py`: disputed lengths, u for v, j for i); Greek's is the form itself until Stage 9.
  - `alternative_tags` (`Medieval-Latin`), `periphrastic` (the forms of sum), `pos_by_head_template` (`la-part`), and `implied_forms`: Latin's participle, comparative and superlative declensions moved to `languages/la_forms.py`; `merge/forms.py` keeps the shared part.
  - The default descendant languages (`--descendants` now defaults to the language's), the homographs the front page names, and `miss_variants`, the retries coverage names a miss's cause with (Latin's enclitics, j for i and u for v, moved from `quality/coverage.py`).
- [x] `kindle_fold` and the corpus tokenizer no longer normalize to NFC: a word is weighed as the text prints it, as the device does (a decomposed ā, a Greek oxia). Labels were already NFC where they are made.
- [x] The weekly workflow passes `--lang` to coverage; `docs/DEVELOPING.md` says how to add a language.
- Left for the Greek stages, where there is something to decide: the headline style and sense-label abbreviations (Stage 10), the spelling `popup_order.py` ranks shared labels by (it ranks only ASCII-folding spellings, so none in Greek; Stage 9), the StarDict synonym rule and the device checklist path (Stage 11).

Measured (2026-10-29, dump of 2026-10-25, kindling v0.45.6): a full Latin build before and after writes identical XHTML pages and OPF, and a `.mobi` of the same size (60,194,891 bytes, 1,662,329 index entries) that differs in 4 bytes of header timestamps. Corpus coverage is unchanged in every source (86.4% of tokens open something, 1.0% left to index order). 174 tests pass, 11 of them new (`tests/test_languages.py`).

Greek smoke build (same dump): the `grc` filter keeps 69,171 lines (395 MB). `--lang grc` builds through the whole pipeline without errors: 21,383 entries, 1,104,887 lookup terms, a 39.9 MB `.mobi`, and kindling's checks pass. Nothing is tuned yet, and 68% of the 1.10M labels still carry macrons or breves (`λῡ́ω`), which no text prints, so those spellings open nothing. Removing them is the first item of Stage 9.

## Stage 8: Ancient Greek — measure first

- [ ] Filter the dump for `grc` and count: entries, pointer pages, forms per entry, forms with length marks, `table-tags` dialects, head templates (`grc-noun`, `grc-adj`, `grc-verb`, `grc-part`?). Build the sample dump (`quality sample --lang grc`) through the Stage 7 pipeline and list what breaks.
- [ ] Corpus `corpus/grc.tsv` from freely licensed TEI texts (Perseus canonical-greekLit and First1KGreek, CC BY-SA 4.0): Iliad 1, Odyssey 1, Herodotus 1, Xenophon's Anabasis 1, Plato's Apology, a speech of Lysias, and a Koine text (the Gospel of John from a public-domain edition). `quality/corpus.py` gains a TEI format. Record each text's Unicode habits: tonos or oxia, precomposed or decomposed, which elision mark.
- [ ] Coverage miss causes for Greek: capital, grave for acute, an enclitic's extra accent, elision, crasis, movable nu, oxia, decomposed, dialect form.
- [ ] Device test book (`scripts/make_device_test.py`, words in `tests/device_words_grc.tsv`), each item predicted from kindling's README first:
  - A capitalized tap (`Ἄνδρα`) and a lowercase label: expected miss.
  - Oxia against tonos, decomposed against precomposed: expected miss.
  - Grave against acute (`καλὸς`, `καλός`): expected miss.
  - Elision marks `ἀλλ’` (U+2019), `ἀλλʼ` (U+02BC), `ἀλλ᾽` (U+1FBD), `ἀλλ'`: which the selection includes, and which weigh nothing.
  - The dictionary declared as `grc` and as `el`: which one Settings → Dictionaries offers for a book declared `grc` and for one declared `el`.
  - Polytonic letters in the popup and in the book (`ᾄ`, `ῷ`, `ἂν`, `᾽`) with the default fonts: no boxes (cf. Gothic, Stage 6).
- [ ] Baseline: entries, labels, folded keys, `.mobi` size, build time, coverage per source. Measurements stay in `outputs/measure/`.

## Stage 9: Ancient Greek — lookups

The device folds nothing in Greek, so each kind of spelling a text prints becomes a label kind. Each is measured as coverage gained per label added; a kind that does not pay is dropped or limited to corpus-attested forms (Lemma's approach).

- [ ] **Without length marks.** Every headword and form gets its spelling without macrons and breves (`λῡ́ουσῐν` → `λύουσιν`): precomposed `ᾱ ῑ ῡ ᾰ ῐ ῠ` lose the mark, combining U+0304 and U+0306 are dropped, and the rest is recomposed to NFC. This is the spelling texts print; the marked one stays only as the displayed headword.
- [ ] **Capitalized.** The first letter of every headword and form capitalized, with the breathing and accent moved onto the capital (`ἄνδρα` → `Ἄνδρα`). Editions capitalize paragraph and speech openings and proper names.
- [ ] **Grave.** A form with an acute on the last syllable gets the grave spelling (`καλός` → `καλὸς`, `ἀγαθόν` → `ἀγαθὸν`), which a text prints before another word.
- [ ] **Enclitics.** Before an enclitic, a proparoxytone or properispomenon form gains an acute on its last syllable (`ἄνθρωπός τις`, `δῶρόν τι`), and the enclitics appear with or without an accent (`ἐστι`, `ἐστί`, `ἐστὶ`, `ἔστι`; `τις`, `τὶς`). Add the enclitics' spellings; add the extra-accent spellings only if the corpus shows they pay.
- [ ] **Movable nu.** Forms in -σι(ν), -ε(ν) and `ἐστί(ν)` get the spelling with or without ν that the table lacks.
- [ ] **Elision and crasis.** Elided forms (`ἀλλ’`, `δ’`, `ἐπ’`, `κατ’`) are indexed where Wiktionary has a page, plus those the corpus attests; the elision mark is the one the device test shows a tap ignores. Crasis (`κἀγώ`, `τοὔνομα`) only where Wiktionary has a page.
- [ ] **Participles.** Wiktionary lists only their nominatives; generate the declension, as Stage 3 did for Latin (`-ων -οντος`, `-ουσα -ούσης`; `-μενος -η -ον`; `-σᾱς -σαντος`; `-θείς -θέντος`; `-ώς -ότος`, `-υῖα`), with the accent kept where the nominative has it as far as the ending allows. Tagged `generated`, skipped where Wiktionary has a page. Comparatives and superlatives the same way, from the forms the lemma tags.
- [ ] **Dialects.** Read the `table-tags` row heading each table, so a form keeps its dialect (Epic, Ionic, Doric, Aeolic, Koine); index all of them.
- [ ] **Popup order.** The estimate works as in Latin. Accents count, so entries tie only on the same accented spelling, mostly forms shared between lemmas; the likeliest gets the plain label, the rest soft hyphens by rank (`shared_labels.py`).
- [ ] **Label budget.** Latin's baseline had 2.99M labels in a 98 MB `.mobi`; the length-free, capitalized and grave spellings could triple Greek's. Measure build time, size and the 65,535-record limit after each kind; if the budget is exceeded, index the costly kinds only for corpus-attested forms.
- [ ] **Book preparation, first use.** If the device test shows oxia or decomposed accents miss and the corpus shows such editions are common, `prepare-book` normalizes the text instead of doubling labels: NFC with oxia as tonos, one elision mark, lunate sigma `ϲ` as `σ`/`ς`. Otherwise this waits for Turkish.
- Done when: every word in `tests/lookup_words_grc.txt` opens, kindling's lookup agrees on the most frequent corpus words, and the remaining misses are listed by cause.

## Stage 10: Ancient Greek — entries

- [ ] Headline in the style of LSJ: `λόγος, -ου, ὁ · noun, 2nd decl.` (the article for the gender: ὁ, ἡ, τό); adjectives `-ος, -η, -ον`; verbs with principal parts taken from the tables where they exist (`λύω, λύσω, ἔλυσα, λέλυκα, λέλυμαι, ἐλύθην`). The headword keeps its length marks.
- [ ] Sense labels shortened: Ep., Att., Ion., Dor., Aeol., Koine, Byz., poet.
- [ ] Default descendant languages for Greek (Latin borrowings are the interesting ones): decide with a sample.
- [ ] Wiktionary's romanization is not shown: the reader is reading Greek script.
- [ ] Merged pointer pages keep their line by kind (`alt.`, `Ep.`, `dim.`), as in Stage 4.

## Stage 11: Ancient Greek — releases

- [ ] `grc` in the workflow matrix, with its own coverage gate against `corpus/grc.tsv`.
- [ ] `docs/device-check-grc.md`, with pre-releases marked as the latest after the check, as for Latin.
- [ ] StarDict: a synonym without accents, breathings and length marks for every label, since KOReader and GoldenDict searches are often typed without them.
- [ ] README: install instructions per language, and what `prepare-book` does if Stage 9 needed it.

## Stage 12: Turkish — outline

From the 2026-10-29 plan; to be detailed after Greek.

- What the device does: lookup matches the whole selected word, with no stemming; `ı`, `İ`, `I` and `i` weigh the same, as do ş/s, ğ/g, ç/c, ö/o, ü/u, so no case variants are needed and `popup_order.py` handles the extra ties. A noun's Wiktionary table gives about 100 forms (102 for `ev`, case × number × possessive), but texts add the copula (`evdeydi`), `-ki`, `-le` and derivations, which no table lists.
- [ ] **Device test (shared with Stage 0's enclitic check):** does a long press stop at U+200B (zero-width space), U+2060 (word joiner), U+200A (hair space) or an apostrophe (`Türkiye'nin`)? Does `white-space: nowrap` keep a word with a zero-width space on one line? Everything in book segmentation depends on this.
- [ ] **Baseline from Wiktionary forms**, measuring labels against the budget; stem variants as labels of their lemma (`kitab` → kitap, `ağz` → ağız, `hakk` → hak, `gid` → git), since they are what a split leaves.
- [ ] **Corpus-attested forms**, lemmatized at build time by an existing analyzer (`zeyrek`, or Zemberek; licences to check), up to the label budget.
- [ ] **`prepare-book` segmentation:** an invisible break between the stem and the suffix chain, only in words the dictionary cannot reach, after the longest stem the dictionary has (`gözlükçü​ler`), so a split never leaves a stem that cannot be looked up. Suffix-chain entries (`-lerinizden`: *pl. + your (pl.) + abl.*) for a tap on the suffixes. Alternative: a personal dictionary with the book's own analyzed forms (`--forms-from`), which leaves the text alone.
- [ ] Releases as in Stage 11.

## Later

- Latin enclitics through `prepare-book` once the device test settles the separator.
- Further inflected languages (Finnish, Hungarian) on the Turkish machinery.
