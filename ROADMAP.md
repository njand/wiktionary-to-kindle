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

## Stage 8: Ancient Greek — measured, device check pending

- [x] **The dump** (raw dump of 2026-10-25, filtered for `grc`: 69,171 entries, 395 MB). 47,646 are pages that only point to a lemma (`grc-noun form`, `grc-verb form`, `grc-adjective form` head templates); the lemmas are mostly `grc-noun` (9,127), `grc-proper noun` (4,266), `grc-verb` (3,098), adjectives by declension (`grc-adj-1&2`, `-2nd`, `-3rd`, `-1&3`) and participles (`grc-part-1&3`, `grc-part-1&2`); 5,763 have no head template. 1.43M table forms: 69% carry macrons or breves, 271 have parentheses, 51,749 have spaces (periphrastic and article forms). Half the entries list no forms; the 90th percentile lists 48, the largest 1,737. Forms are tagged with person, number, mood, voice, case and gender, but **not tense**: the tense, and the dialect (Attic, Epic, Ionic, Doric, Koine), are in the `table-tags` row heading each table (`Epic aorist`, `Ionic declension-2`), which the build skips.
- [x] **What the Stage 7 pipeline does with it.** It builds (Stage 7). Entries render, with three things for Stage 10: the head line is Wiktionary's whole (`λόγος • (lógos) m (gen. λόγου); 2nd decl.`), repeating the headword, with its length marks, and the romanization; descendants show `Latin` unshortened; and εἰμί gets `alt. ἔῃ`, a pointer page whose gloss starts "alternative form" (to check). An entry's main label is its page title, so lemmas open; their table forms do not where they carry length marks, unless a merged page of their own gives the plain spelling (`λύουσιν` opens λύω through its page).
- [x] **Corpus** `corpus/grc.tsv`: seven Perseus canonical-greekLit editions (CC BY-SA 4.0), 72,830 tokens: Iliad 1, Odyssey 1, Herodotus 1, Anabasis 1, Plato's Apology, Lysias 1 and John (Westcott–Hort, Perseus's edition; the public-domain one planned is not in canonical-greekLit). `quality/corpus.py` reads TEI (`tei`, or `tei:N` for one book) without notes, headings and the header. Unicode habits, the same in all seven: tonos, no oxia; every accent precomposed; elision with U+02BC (`δʼ`), which weighs nothing on the device. 25% of tokens have a grave (`καὶ` alone is 4.5%) and 7% are capitalized.
- [x] **Miss causes** (`grc.miss_variants`): oxia or decomposed, capitalized, grave for acute, an enclitic's accent, movable nu (only -ε, -σι and -στι take one: an accusative's or infinitive's ν is none), elision (each short vowel, with an acute when the rest has none, after θ φ χ deaspirated). Crasis and dialect forms are not guessed and count as unknown.
- [x] **Baseline** (the Stage 7 smoke build): 21,383 entries, 1,100,786 labels, 1,045,158 folded keys, 31,184 tied keys, at most 1,724 labels per entry, a 39.9 MB `.mobi`. Coverage: **61.9%** of tokens open something (Homer 69–72%, Herodotus 57%, Attic prose 62–65%, John 65%); 0.9% are left to index order. Of the misses: grave for acute 16,472 tokens (22.6% of all), unknown 8,583, unknown and capitalized 1,495, an enclitic's accent 521, capitalized 426, capitalized and grave 125, elision 54, movable nu 31. Elided `δʼ` already opens δέ: Wiktionary has elided forms, and the mark weighs nothing. Measurements: `outputs/measure/stats-grc-stage8.json`, `coverage-grc-baseline.*`.
- [x] **What Stage 9 can gain**, on the same build and corpus: labels without length marks alone take coverage from 61.9% to 68.3% (`ἀπεκρίθη`, `εἶπαν`, `αἰώνιον` and Ionic `ἐόντας` lead); the spelling kinds above alone to 86.2%; both to 92.9%. The rest is mostly names (`Σάρδις`, `Λυδῶν`), Ionic forms (`τούτοισι`, `χρέωνται`) and crasis.
- [ ] **Device test book**: `scripts/make_device_test.py --lang grc` (the script now takes any language, and a `ύ`-style escape in a word list stands for that character) with `tests/device_words_grc.tsv`, 32 words: frequent words, capitals, grave, enclitic and movable-nu accents, oxia and decomposed encodings, four elision marks, length marks, breathings and iota subscripts (do they render?), a final σ. kindling predicts a miss for every capital, grave, oxia, decomposed accent, the koronis and the final σ, and δέ for `δʼ` and `δ’`. Built locally into `outputs/device-test-grc/`, beside the dictionary; to check on a Kindle.
- [ ] Still to check on the device: whether the selection takes in an elision mark at all, and which dictionary language (`grc` or `el`) Settings offers for a book declared `grc` (needs a second build declared `el`).

## Stage 9: Ancient Greek — lookups — done, device check pending

The device folds nothing in Greek, so each kind of spelling a text prints becomes a label kind. Each is measured as coverage gained per label added; a kind that does not pay is dropped or limited to corpus-attested forms (Lemma's approach).

Measured kind by kind on the full dump and `corpus/grc.tsv` (72,830 tokens), each build adding one kind to the last (log: `outputs/measure/grc-spelling-kinds.log`):

| Spellings | Labels | `.mobi` | Build | Tokens that open |
| --- | ---: | ---: | ---: | ---: |
| Stage 8 baseline (as Wiktionary spells them) | 1,100,786 | 39.9 MB | | 61.9% |
| without length marks | 1,044,916 | 37.6 MB | 69 s | 68.3% |
| + movable nu | 1,191,760 | 43.2 MB | 78 s | 68.3% |
| + grave for a final acute | 1,294,733 | 45.9 MB | 84 s | 91.2% |
| + capitals, every form | 2,522,527 | 85.2 MB | 126 s | 92.0% |
| + an enclitic's second accent | 5,248,043 | 178.8 MB | 248 s | 92.8% |
| **kept: no length marks, grave, capitals for headwords and closed-class words** | **1,172,137** | **41.0 MB** | **74 s** | **91.7%** |

- [x] **Without length marks.** `grc.lookup_spellings` labels every headword and form without macrons and breves (`λῡ́ουσῐν` → `λύουσιν`); the marked spelling is no label, since no text prints it. +6.4 points.
- [x] **Grave.** A form with an acute on its last syllable also gets the grave (`καλός` → `καλὸς`, `καί` → `καὶ`): +22.9 points for 8% more labels, the best kind by far.
- [x] **Capitals, for some entries.** Capitalizing every form doubled the labels for 0.8 points. `Language.capitalizes(pos, headword)` now decides: every headword, and every form of a pronoun, article, particle, conjunction, preposition, adverb, interjection or numeral (`Καὶ`, `Ὁ`, `Οὐκ`, `Ταῦτα`), which were most of the capitalized misses. 6% more labels; capitalized misses fall from 551 tokens to 216 (`Κύριε`, `Ἴδε`, `Λέγει`: forms of open-class words). Latin never capitalizes: the device folds its case. `utils.capitalized` uses titlecase, so an iota subscript stays one letter (`ᾨδή`).
- [x] **Movable nu: dropped.** The spelling with or without ν adds 14% labels and no tokens: the tables already have the spelling texts use, or the form has a page.
- [x] **An enclitic's second accent: dropped.** `ἄνθρωπός τις` spellings double the labels again for 0.8 points (616 tokens, mostly pronouns: `ταῦτά`, `οὗτός`, `τοῦτό`). Limiting them to closed-class words, like capitals, is the next thing to try; the rule (count syllables, diphthongs as one; an acute on the antepenult or a circumflex on the penult gains an acute on the last) was written for the measurement and not kept.
- [x] **Elision and crasis.** Nothing to add: Wiktionary has pages for the common elided forms, Perseus's U+02BC weighs nothing, so `δʼ` and `ἀλλʼ` open δέ and ἀλλά already. 65 elided tokens still miss (`εἴτʼ`, `πράγματʼ`). Crasis stays at what Wiktionary has.
- [ ] **Participles: deferred.** About 1,160 missed tokens (1.6%) look like participles, but many are Ionic (`ἀπικόμενοι`, `καλεομένης`) or verbs whose table is missing; a generated declension of every table participle (with the accent moved by the ultima's length) would about double the labels for under a point.
- [ ] **Dialects: deferred.** The `table-tags` rows are skipped; reading them changes no label, only what an entry could say about a form.
- [x] **Popup order.** Nothing to change: a tap reaches only labels spelled the same, and `shared_labels.py` gives the likeliest entry the plain label and the rest soft hyphens by the estimate, which kindling lists in that order (`εἶ`: εἰμί, εἶμι, then the letter's name). `popup_order.rank_spellings` only ranks spellings that fold to ASCII, so it leaves Greek alone.
- [x] **Label budget.** 1.17M labels and 41 MB, below Latin's 1.66M and 60 MB; the 300 most frequent corpus words agree with kindling's simulator, and no label is hidden.
- [x] **Book preparation: not needed** for these editions: Perseus prints NFC with tonos, precomposed accents and an elision mark that weighs nothing. The device test will say whether oxia texts need it.
- [x] Done: every word in `tests/lookup_words_grc.txt` opens (three known gaps marked `xfail`: a capitalized noun form, an enclitic's accent, an Ionic form), kindling's lookup agrees on the 300 most frequent corpus words, and the remaining misses are listed by cause.

- [x] **Both orthographies (2026-10-29, after Stage 11).** Editions that mark long vowels (school texts) print spellings the labels above lacked, and a Kindle folds no length mark, so `grc.long_marked` adds each form as such an edition prints it: Wiktionary's macrons kept, its breves dropped (short vowels are left plain), a disputed vowel (`ῡ̆`) both ways, each with its grave. A long vowel with a breathing or accent has no letter of its own, so its marks come in two orders, and both are labels: Wiktionary's macron first (`ῑ̓όν`, U+1FD1 then the breathing) and the accented letter with the macron after it (`ἰ̄όν`, U+1F30 then U+0304), as polytonic keyboards type it. A marked tap reaches only the forms with those lengths: 2,633 marked spellings narrow a plain one that reaches several entries (`ῑ̓όν` opens only ἰός "arrow", where `ἰόν` also reaches forms of εἶμι and ἐγώ; `ἰδῑ́ων` only ἰδίω). Cost: 998,072 → 1,181,278 labels (+18%), 34.2 → 39.6 MB, 101 s; unmarked coverage unchanged (91.7%), kindling agrees on the 300 most frequent words, and the lookup list's marked words open. Coverage names a marked word that misses "length marks" (marked where Wiktionary marks none). No length-marked corpus text is in `corpus/grc.tsv` yet, so how often an edition's marking matches Wiktionary's is unmeasured.

A full Latin build after this stage writes pages and an OPF identical to Stage 7's (capitals are never added for Latin).

Remaining misses (8.3% of tokens): unknown 4,358 tokens, mostly Herodotus's Ionic forms (`τούτοισι`, `χρέωνται`, `ἀπίκοντο`; Herodotus opens 87.8%, the rest 93–95%), Koine words (`καθὼς`) and names; capitalized names 795; an enclitic's accent 616; capitalized open-class forms 216; elision 65. Measurements: `outputs/measure/stats-grc-stage9.json`, `coverage-grc-stage9.*`. The device test book is rebuilt against this dictionary (`outputs/device-test-grc/`).

## Stage 10: Ancient Greek — entries — done, device check pending

- [x] **Head line.** Greek head lines (`λόγος • (lógos) m (genitive λόγου); second declension`) now parse like Latin's: `models/header.py` finds a headword with accents of its own in the head line (it compared the page title's accents with the line stripped of them, so no Greek headword was found and the whole line was shown). `Language.head_line` drops the romanization, and an adjective's leading gender; `Language.genders` shows the gender by the article. Result: `λόγος, λόγου ὁ · noun, 2nd decl.`, `ᾰ̓γᾰθός, ᾰ̓γᾰθή, ᾰ̓γᾰθόν · adjective, 1st/2nd decl.`, `χώρᾱ, χώρᾱς ἡ · noun, 1st decl.`; the headword is shown as the head line spells it, with its length marks. The genitive is given whole, not as LSJ's ending (`-ου`).
- [ ] **Verbs' principal parts: deferred.** Greek verb head lines name none, and the tables tag no tense (Stage 8), so the parts would have to come from the `table-tags` rows; verbs show `λῡ̆́ω · verb`.
- [x] **Filed by page title.** `Language.headword` gives the spelling an entry is filed and labelled under: Latin's head line (macronized, which form-of targets name), Greek's page title (what texts print and form-of links name; the head line is less reliable: `ᾱ́ζω` for ἄζω, without its breathing, `ἀθρᾰ́γένη` with two accents). Filing Greek by the head line instead broke merges (ἀνάσσω's forms became entries).
- [x] **Sense labels.** Ep., chiefly Ep., Hom., Att., Ion., Dor., Aeol. (no Latin gloss uses these). Koine stays as it is.
- [x] **Descendants.** Greek entries keep Modern Greek (cited by 6,833 entries), Latin (5,600) and English (2,671), shown as `Mod. Gk.`, `Lat.`, `Eng.`.
- [x] **Romanization** is not shown (`head_line` drops it).
- [x] **Merged pages.** A page reached through an inflected form is no spelling of the lemma and gets no line: εἰμί's `alt. ἔῃ` came from ἔῃ, "alternative form of ᾖ", the subjunctive. `collect_forms` now gives a line only to pages reached through the lemma or another page with a line. Greek merged pages are mostly `alt.` (544), `comp.`, `superl.`; dialect forms ("Epic form of") are forms, with no line, as in Latin.
- [x] **Found on the way, in the Greek tables:** 1,713 verbs listed εἰμί's optatives (`εἶεν`, `εἶτε`, `εἴτην`, `εἶτον`, `εἶμεν`), which Kaikki splits off the periphrastic perfect optative (`λελυμένοι εἶεν`); 24,516 forms are romanizations or table notes (`tēîsĭnĭ`, `third declension`, `first`, which 638 entries shared); some forms end in σ for ς (`ἀγαπήσῃσ`). `Language.skips_form` (Latin: its periphrastic forms) now drops the first two, and Greek labels write a final σ as ς.

Measured (same dump; `SORT_VERSION` 10): Greek has 21,383 entries (unchanged), 998,072 labels (from 1,172,137; 1,181,278 with the long-marked spellings added after Stage 11), a 34.2 MB `.mobi`, and still opens 91.7% of corpus tokens; every word in `tests/lookup_words_grc.txt` opens. Latin: 192 entries change, all by losing `alt.` lines for spellings of participles and other forms (`adhaereō` loses `adhēsūrus`, `adnotō` loses `annotandus`, `annotātūrus`, `annotāns`); nine of them change labels without changing what a tap reaches (three pages now take their headword from the head line, `m͛cātor` for `m͛cator`; six only swap soft-hyphen ranks, their size estimates having changed). Latin coverage is unchanged in every source. The device test book is rebuilt (`outputs/device-test-grc/`).

## Stage 11: Ancient Greek — releases — done, first device check pending

- [x] `grc` in the workflow matrix. The workflow was already language-neutral: each language finds its corpus (`corpus/grc.tsv`, the coverage gate), lookup list (`tests/lookup_words_grc.txt`) and device checklist by its code, and both languages go into one pre-release. Greek's first build has no coverage in the latest release, so its gate starts after the first release marked as the latest. Checked locally (Actions quota): the coverage step with kindling's check (300/300 agree), the lookup list (0 unexpected misses), and the release-notes step, which gives Greek its index note, coverage table and checklist.
- [x] `docs/device-check-grc.md`: where Settings lists the dictionary (it declares `grc`), the front page, graves and capitals (`καὶ`, `Καὶ`), popup order (`εἶ`, `θεός`), a length-marked form (`ἀπεκρίθη`), elision (`δʼ`), the two predicted misses that would show the device folds more than kindling says (`Ἄνδρα`, an oxia `λύω`), the head line, and polytonic rendering; each prediction checked with kindling. Then the 32-word test book.
- [x] StarDict needed nothing: `stardict.unaccented` drops every combining mark but abbreviation signs, so each Greek label gets a synonym without accents, breathings or iota subscript (`λογος`, `και`, `απεκριθη`, `ωδη` → ᾠδή and ἀοιδός; `ειμι` → εἰμί and εἶμι). The bundle (`grc-wiktionary-stardict.zip`, 8.3 MB) holds 21,383 words and 1,901,816 synonyms, titled "Ancient Greek-English Dictionary (grc-en)".
- [x] README: an "Ancient Greek (in testing)" section (pre-releases only until a device check; what a lookup does; coverage), the Greek `.mobi` and StarDict files in the install steps, and that the language Settings lists it under is still being checked. `prepare-book` was not needed (Stage 9). The developer guide's Releases section names both checklists.

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
