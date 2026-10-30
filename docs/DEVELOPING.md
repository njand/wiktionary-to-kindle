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
| `--lang <code>` | Language code to build (default: `la`). |
| `--input <path>` | Build from a local `.jsonl` file instead of downloading. |
| `--no-download` | Use the file already in `downloads/` instead of downloading a new one. |
| `--resort` | Sort the data again even if a cached sorted file is up to date. |
| `--kindling <path>` | Location of `kindling-cli`, if it isn't on your `PATH`. `--kindlegen` is accepted as an older name. |
| `--stardict` | Also write `<lang>-wiktionary-stardict.zip` for KOReader and GoldenDict. |
| `--descendants <names>` | Languages to keep in each entry's list of descendants (default: English Portuguese Spanish French Italian). |

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

`coverage` checks how many words in a set of real Latin texts (`corpus/la.tsv`) open an entry and explains why the rest don't, following the Kindle's own matching rules. Add `--kindling <binary> --mobi <file>` to also check the most frequent words with kindling's on-device lookup simulator.

`coverage-diff` compares two coverage reports. With `--fail-on-drop` it exits with an error when any source's coverage falls by more than half a percentage point (adjustable with `--threshold`).

## Releases

A scheduled GitHub Actions workflow builds the dictionary every Sunday and publishes it as a pre-release with the `.mobi`, the StarDict bundle, and the statistics and coverage reports. The build fails if coverage drops compared with the latest release. To publish an intentional drop, run the workflow manually with **Allow a coverage drop** checked.

Each release's notes end with a [device checklist](device-check-la.md). Once a build has been checked on a Kindle, it is marked as the latest release, and the next build compares its coverage against it.

## Adding a language

1. Add any language-specific normalization or tag parsing to `wiktionary_to_kindle/models/`.
2. Add the language code to the build matrix in `.github/workflows/dictionary-build.yml`.
3. Open a pull request.

## Data dates

The build takes the data's date from Kaikki's `Last-Modified` header and stores it in `downloads/<file>.date`. When you build from your own file with `--input`, put its date in a `<file>.date` file next to it. Otherwise the file's modification date is used.
