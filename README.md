# Wiktionary to Kindle

[![Build and Release Dictionaries](https://github.com/njand/wiktionary-to-kindle/actions/workflows/dictionary-build.yml/badge.svg)](https://github.com/njand/wiktionary-to-kindle/actions/workflows/dictionary-build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A free Latin dictionary for your Kindle, built from Wiktionary.**

Press and hold any Latin word in a book — *amāverat*, *cujus*, *uirum* — and the dictionary opens the right entry, with its meanings, principal parts and etymology. Every inflected form is indexed, so you don't need to know the dictionary form to look a word up.

The dictionary is rebuilt every week from the latest Wiktionary data. The same build is also available in StarDict format for KOReader and GoldenDict.

> [!TIP]
> **Just want the dictionary?** Download the `.mobi` file from the **[latest release](https://github.com/njand/wiktionary-to-kindle/releases/latest)** and follow the [installation steps](#install-on-a-kindle) below. You don't need to build anything.

## Contents

- [Install on a Kindle](#install-on-a-kindle)
- [Use with KOReader or GoldenDict](#use-with-koreader-or-goldendict)
- [What's in the dictionary](#whats-in-the-dictionary)
- [Build it yourself](#build-it-yourself)
- [How it works](#how-it-works)
- [Measuring lookup quality](#measuring-lookup-quality)
- [Contributing](#contributing)
- [License and credits](#license-and-credits)

## Install on a Kindle

### 1. Copy the file to your Kindle

1. Download `la-wiktionary.mobi` from the [latest release](https://github.com/njand/wiktionary-to-kindle/releases/latest).
2. Connect your Kindle to your computer with a USB cable.
3. Open the Kindle drive and go to `documents/dictionaries/`. If there is no `dictionaries` folder, create one inside `documents`.
4. Copy the `.mobi` file into `documents/dictionaries/`.
5. Eject the Kindle and unplug it.

> [!NOTE]
> Send to Kindle no longer accepts `.mobi` files, and a dictionary only works from the `dictionaries` folder, so it has to be copied over USB.

### 2. Make it your Latin dictionary

On the Kindle, open **Settings → Device Options → Language and Dictionaries → Dictionaries**, tap **Latin**, and choose the Wiktionary dictionary.

### 3. Look up a word

Open a Latin book and press and hold a word. If another dictionary opens, tap its name at the bottom of the popup to switch.

When a spelling belongs to more than one word, swipe across the popup to see the others. The word you most likely meant comes first.

## Use with KOReader or GoldenDict

Each release also includes `la-wiktionary-stardict.zip`. Unzip it, then:

- **KOReader:** copy the `la-wiktionary` folder into `koreader/data/dict/`.
- **GoldenDict:** add the `la-wiktionary` folder to your dictionary sources.

## What's in the dictionary

- **Every form of every word.** Inflected forms point to their lemma, including participles, comparatives and superlatives that Wiktionary only implies.
- **Any spelling convention.** Lookups work with or without macrons (*amō*, *amo*), with *u* or *v* (*uir*, *vir*), and with *i* or *j* (*iam*, *jam*). Alternative and Medieval Latin spellings are indexed too.
- **Homographs kept apart.** Words that share a spelling (*latus* "side", *lātus* "carried") are separate entries, ordered so the more likely one appears first.
- **Related words in one place.** Diminutives and alternative forms appear in their lemma's entry, with a short gloss where Wiktionary gives one.
- **Compact entries.** Each entry is laid out like a print dictionary — headword line, numbered senses, etymology — and sized for the lookup popup.

> [!IMPORTANT]
> Only Latin is built and tested today. The pipeline itself is designed to be language-agnostic; see [Contributing](#contributing) if you'd like to add another language.

## Build it yourself

### Requirements

- **Python 3.10 or later**
- **[kindling](https://github.com/ciscoriordan/kindling/releases)** (`kindling-cli`) to compile the `.mobi`. Amazon's `kindlegen` is not supported. Put `kindling-cli` on your `PATH` or pass its location with `--kindling`. The automated builds use v0.45.6.
- **Recommended:** [uv](https://docs.astral.sh/uv/) to manage dependencies, and `ripgrep` and `pigz` for faster extraction of the Wiktionary dump. Without them the build falls back to pure Python.

### Set up

```bash
git clone https://github.com/njand/wiktionary-to-kindle.git
```

```bash
cd wiktionary-to-kindle
```

```bash
uv sync --all-extras
```

### Build

```bash
uv run wiktionary-to-kindle --lang la
```

This downloads the Latin data from [Kaikki.org](https://kaikki.org/), sorts and merges it, renders the entries and compiles the dictionary. The result is written to `outputs/KindleDictionary-la/la-wiktionary.mobi`.

The first build downloads a large file and takes a while. Later builds reuse the sorted data as long as the download hasn't changed.

### Options

| Option | Description |
| --- | --- |
| `--lang <code>` | Language code to build (default: `la`). |
| `--input <path>` | Build from a local `.jsonl` file instead of downloading. |
| `--no-download` | Use the file already in `downloads/` instead of downloading a new one. |
| `--resort` | Sort the data again even if a cached sorted file is up to date. |
| `--kindling <path>` | Location of `kindling-cli`, if it isn't on your `PATH`. (`--kindlegen` is accepted as an older name.) |
| `--stardict` | Also write `<lang>-wiktionary-stardict.zip` for KOReader and GoldenDict. |
| `--descendants <names>` | Languages to keep in each entry's list of descendants (default: English Portuguese Spanish French Italian). |

### Run the tests

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

### Working around Kindle's limits

A Kindle's lookup engine has constraints that shape the output:

- **The popup shows every entry a tap reaches**, with an exact spelling match first. Each entry is indexed under all of its spellings, and when a tap has no macrons the build decides which entry gets the plain spelling. Wiktionary has no word frequencies, so the build estimates them from how much Wiktionary says about each word: *non* opens *nōn* before *nōnae*.
- **Matching ignores macrons and case, but not *u*/*v* or *i*/*j*.** Entries carry macronized labels, disputed vowel lengths (*ā̆*) get both spellings, and *u*/*j* spellings are added explicitly.
- **The popup applies no stylesheet**, and kindling strips `class` attributes, so entries use `<b>` and `<i>` for formatting instead of CSS.

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

- **`stats`** summarizes a build's index; **`diff`** compares two builds.
- **`coverage`** checks how many words in a set of real Latin texts (`corpus/la.tsv`) open an entry, and explains why the rest don't. It follows the Kindle's own matching rules. Add `--kindling <binary> --mobi <file>` to also check the most frequent words with kindling's on-device lookup simulator.
- **`coverage-diff`** compares two coverage reports. With `--fail-on-drop` it exits with an error when any source's coverage falls by more than half a percentage point (adjustable with `--threshold`).

### Faster development builds

A full build processes the whole dump. For quicker iterations, build from a small, self-consistent sample:

```bash
uv run python -m wiktionary_to_kindle.quality sample downloads/kaikki-la.jsonl downloads/sample-la.jsonl
```

```bash
uv run wiktionary-to-kindle --lang la --no-download --input downloads/sample-la.jsonl
```

### Releases

A scheduled GitHub Actions workflow builds the dictionary every Sunday and publishes it as a pre-release with the `.mobi`, the StarDict bundle, and the statistics and coverage reports. The build fails if coverage drops compared with the latest release; to publish an intentional drop, run the workflow manually with **Allow a coverage drop** checked.

Each release's notes end with a [device checklist](docs/device-check-la.md). Once a build has been checked on a Kindle, it is marked as the latest release, and the next build compares its coverage against it.

## Contributing

Contributions are welcome — bug reports, lookup failures you've noticed while reading, and code alike.

To add a language (for example, Ancient Greek or French):

1. Add any language-specific normalization or tag parsing to `wiktionary_to_kindle/models/`.
2. Add the language code to the build matrix in `.github/workflows/dictionary-build.yml`.
3. Open a pull request.

## License and credits

The code is released under the [MIT License](LICENSE).

The dictionary content comes from [Wiktionary](https://www.wiktionary.org/), extracted by [Kaikki.org](https://kaikki.org/), and is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Each dictionary is distributed under that license and opens with a page that credits Wiktionary's contributors and Kaikki.org, states the license, and gives the dates of the data and the build.

The build takes the data's date from Kaikki's `Last-Modified` header and stores it in `downloads/<file>.date`. When you build from your own file with `--input`, put its date in a `<file>.date` file next to it; otherwise the file's modification date is used.
