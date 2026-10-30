# Developing

This guide covers building the dictionary from source, how the pipeline is put together, and the tools that measure lookup quality. For installing the finished dictionary, see the [README](../README.md).

## Requirements

- Python 3.10 or later.
- [kindling](https://github.com/ciscoriordan/kindling/releases) (`kindling-cli`) to compile the `.mobi`. Amazon's `kindlegen` is not supported. Put `kindling-cli` on your `PATH` or pass its location with `--kindling`. The automated builds use v0.45.6.
- Recommended: [uv](https://docs.astral.sh/uv/) to manage dependencies, and `ripgrep` and `pigz` for faster extraction of the Wiktionary dump. Without them the build falls back to pure Python.

## Building

```bash
git clone https://github.com/njand/wiktionary-to-kindle.git
```

```bash
cd wiktionary-to-kindle
```

```bash
uv sync --all-extras
```

```bash
uv run wiktionary-to-kindle --lang la
```

The build downloads the Latin data from [Kaikki.org](https://kaikki.org/), sorts and merges it, renders the entries and compiles the dictionary to `outputs/KindleDictionary-la/la-wiktionary.mobi`.

The first build downloads a large file and takes a while. Later builds reuse the sorted data as long as the download hasn't changed.

### Options

| Option | Description |
| --- | --- |
| `--lang <code>` | Wiktionary language code to build: `la` (default) or `grc`, which is not usable yet. |
| `--input <path>` | Build from a local `.jsonl` file instead of downloading. |
| `--no-download` | Use the file already in `downloads/` instead of downloading a new one. |
| `--resort` | Sort the data again even if a cached sorted file is up to date. |
| `--kindling <path>` | Location of `kindling-cli`, if it isn't on your `PATH`. `--kindlegen` is accepted as an older name. |
| `--stardict` | Also write `<lang>-wiktionary-stardict.zip` for KOReader and GoldenDict. |
| `--descendants <names>` | Languages to keep in each entry's list of descendants (default: chosen for each language; for Latin, English Portuguese Spanish French Italian). |

### Faster development builds

A full build processes the whole dump. To iterate quickly, build from a small, self-consistent sample of it:

```bash
uv run python -m wiktionary_to_kindle.quality sample downloads/kaikki-la.jsonl downloads/sample-la.jsonl
```

```bash
uv run wiktionary-to-kindle --lang la --no-download --input downloads/sample-la.jsonl
```

### Tests

```bash
uv run pytest
```

## How it works

`pipeline.build_dictionary` runs these stages in order. Each one lives in its own module under `wiktionary_to_kindle/`.

| Stage | Module | What it does |
| --- | --- | --- |
| Language | `languages/` | Holds what each language does its own way (see [Adding a language](#adding-a-language)). Every later stage takes the language chosen with `--lang`. |
| Ingest | `ingest.py` | Downloads the Wiktionary data from Kaikki.org, keeps the target language's entries, and records the date of the data. |
| Merge | `merge/` | Sorts the entries on disk, so the multi-gigabyte dump never has to fit in memory. Folds pages that only point to a lemma (inflected forms, alternative spellings) into that lemma, generates implied forms (`forms.py`), and adds lines for related words (`related.py`). The result is cached next to the input. |
| Model | `models/` | Parses the merged data into `Entry`, `Header`, `Sense` and `Inflection` objects and normalizes grammatical tags. |
| Render | `render/` | Writes the entries and the front page as XHTML using Kindle's dictionary markup (`idx:entry`, `idx:orth`, `idx:infl`). |
| Compile | `compiler.py` | Writes the `.opf` package and runs kindling to produce the `.mobi`. |
| StarDict | `stardict.py` | With `--stardict`, converts the same package to StarDict and adds spellings without macrons, since StarDict readers don't ignore them the way a Kindle does. |

### Kindle's lookup rules

The Kindle's lookup engine shapes much of the output.

The popup lists every entry a tap reaches, with an exact spelling match first. Each entry is indexed under all of its spellings, and when a tap has no macrons the build decides which entry gets the plain spelling. Wiktionary has no word frequencies, so the build estimates them from how much Wiktionary says about each word. That is why *non* opens *nōn* before *nōnae*.

Matching ignores macrons and case, but not *u*/*v* or *i*/*j*. Entries carry macronized labels, disputed vowel lengths (*ā̆*) get both spellings, and spellings with *u* and *j* are added explicitly.

The popup applies no stylesheet, and kindling strips `class` attributes, so entries use `<b>` and `<i>` for formatting instead of CSS.

## Measuring lookup quality

The `quality` module reports how well a build serves real texts.

```bash
uv run python -m wiktionary_to_kindle.quality stats outputs/KindleDictionary-la -o stats.json
```

```bash
uv run python -m wiktionary_to_kindle.quality diff old-stats.json stats.json
```

```bash
uv run python -m wiktionary_to_kindle.quality coverage outputs/KindleDictionary-la corpus/la.tsv -o coverage
```

```bash
uv run python -m wiktionary_to_kindle.quality coverage-diff old-coverage.json coverage.json --fail-on-drop
```

`stats` summarizes a build's index, and `diff` compares two builds.

`coverage` checks how many words in a set of real texts (`corpus/la.tsv`, with `--lang` for another language) open an entry and explains why the rest don't, following the Kindle's own matching rules. Words are weighed as the text prints them, without Unicode normalization, as a Kindle does. Add `--kindling <binary> --mobi <file>` to also check the most frequent words with kindling's on-device lookup simulator.

`coverage-diff` compares two coverage reports. With `--fail-on-drop` it exits with an error when any source's coverage falls by more than half a percentage point (adjustable with `--threshold`).

## Releases

A scheduled GitHub Actions workflow builds every language in its matrix (Latin, Ancient Greek and Turkish) every Sunday afternoon (UTC, after Kaikki's weekly dump) and publishes them in one pre-release, each with its `.mobi`, StarDict bundle, and statistics and coverage reports. If Kaikki's dump is the one the `latest-build` release was made from (its `dump-date.txt`), the scheduled run stops before building, since the build would only repeat it; a manual run always builds. The build fails if a language's coverage drops compared with the latest release. To publish an intentional drop, run the workflow manually with **Allow a coverage drop** checked.

The same run copies the `.mobi` and StarDict files to the `latest-build` pre-release, which it overwrites each week, so the README can link to each language's newest build at an address that doesn't change. The Latin `.mobi` link points at the release marked Latest instead.

Each release's notes open with one table of its dictionaries (entries, how many corpus words open an entry, and the change since the latest release), written by `python -m wiktionary_to_kindle.quality notes`. Below it, folded away, are each language's index and coverage tables and its device checklist ([Latin](device-check-la.md), [Ancient Greek](device-check-grc.md), [Turkish](device-check-tr.md)). Turkish's notes also show how a book prepared with `prepare-book --decide rooted` reads. Once a build has been checked on a Kindle, it is marked as the latest release, and the next build compares its coverage against it. A language's first build has no coverage in the latest release to compare with, so its gate starts with the release after the first one marked as the latest.

## Adding a language

Everything a language does its own way is in a `Language` profile in `wiktionary_to_kindle/languages/` (`la.py` for Latin, `grc.py` for Ancient Greek, `tr.py` for Turkish):

- its Wiktionary code and name, which name the dictionary, its lookup index and the section form-of links point to;
- the spellings of a form a tap should find (Latin adds u for v, j for i and both lengths of a disputed vowel);
- the letters a form-of target is matched by when it names a page title instead of a headword;
- the tags of alternative spellings, forms made with an auxiliary, and parts of speech known by their head template;
- the regular forms an entry implies (Latin's participle and comparative declensions, in `la_forms.py`; Turkish's copula, `-(y)lA`, `-ki` and stem variants, in `tr_forms.py`);
- entries of its own making (Turkish's suffix chains, in `tr_suffixes.py`);
- the default descendant languages, the homographs the front page shows, and the variants coverage retries a missed word with.

To add a language:

1. Write its profile and register it in `languages/__init__.py`.
2. Add a corpus (`corpus/<code>.tsv`) and a device checklist.
3. Add the language code to the build matrix in `.github/workflows/dictionary-build.yml`.
4. Open a pull request.

## Preparing books (Turkish)

Turkish stacks suffixes beyond what any table lists, so a Turkish book is prepared before reading: `prepare-book` (`wiktionary_to_kindle/prepare/`) puts a hair space (U+200A) between the stem and the suffixes of each word the dictionary cannot reach whole, so a tap on either half opens its own entry.

```bash
uv sync --extra segment                      # the anthropic package, for the model
uv run prepare-book book.epub                # writes book-prepared.epub and a report
uv run prepare-book book.epub --decide rooted --kindling kindling-cli
```

- `segment.py` finds the candidate splits: the stem must open a word of the built dictionary (read back by `lexicon.py` and cached as `lexicon.json.gz` beside it) and the rest must be a chain the suffix grammar (`languages/tr_suffixes.py`) spells after that stem.
- `model.py` has Claude choose among them, sentence by sentence (`claude-opus-5-5` at effort `low` by default; `--model`, `--effort`, `--backend claude-cli`). Credentials are the Anthropic SDK's (`ANTHROPIC_API_KEY` or an `ant auth login` profile). Each decision is cached beside the book (`book.splits.jsonl`), so a rerun is free and gives the same book. Without a model it splits by the stem of the word's lemma (`--decide rooted`); `--decide export` writes the requests to answer elsewhere.
- `epub.py` rewrites the text between tags only, and wraps each split word in `white-space: nowrap`.

`scripts/measure_prepared.py` measures how a corpus reads after preparation, and `scripts/eval_segmenter.py` scores decisions against a treebank's gold lemmas. Decisions taken while building it are in [decisions-tr.md](decisions-tr.md).

## Data dates

The build takes the data's date from Kaikki's `Last-Modified` header and stores it in `downloads/<file>.date`. When you build from your own file with `--input`, put its date in a `<file>.date` file next to it. Otherwise the file's modification date is used.
