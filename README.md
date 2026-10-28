# Wiktionary-to-Kindle

[![Build and Release Dictionaries](https://github.com/njand/wiktionary-to-kindle/actions/workflows/dictionary-build.yml/badge.svg)](https://github.com/njand/wiktionary-to-kindle/actions/workflows/dictionary-build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Python parser and rendering engine that converts large-scale [Kaikki](https://kaikki.org/) Wiktionary dumps into Kindle dictionaries (`.mobi`) with functional lookup for all inflected forms.

> [!TIP]
> **Looking to install the Latin dictionary on your Kindle?**  
> You do not need to build the project from source. Download the pre-compiled `.mobi` file directly from **[GitHub Releases](https://github.com/njand/wiktionary-to-kindle/releases/latest)** and follow the installation instructions below.

---

## 📱 How to Install & Use on Your Kindle

### 1. Transfer the Dictionary via USB
1. Connect your Kindle to your computer via USB.
2. Open the Kindle storage drive and navigate to the **`documents/dictionaries/`** folder. *(If the `dictionaries` folder does not exist, create it inside `documents/`)*.
3. Copy the downloaded `.mobi` file into `documents/dictionaries/`.
4. Safely eject and unplug your Kindle.

> [!NOTE]
> Amazon's "Send to Kindle" service no longer supports `.mobi` uploads. Direct USB transfer into the `documents/dictionaries/` directory is required for Kindle OS for system lookup dictionaries.

### 2. Set as Default Dictionary
1. Open your Kindle and navigate to **Settings** → **Device Options** → **Language and Dictionaries** → **Dictionaries**.
2. Tap the language for your dictionary (e.g., **Latin**).
3. Select the newly transferred Wiktionary dictionary to set it as the primary lookup tool.

### 3. Using Instant Lookups
* Open any book on your Kindle written in the target language.
* Press and hold any word to trigger the dictionary lookup card.
* If a different dictionary opens by default, tap the dictionary title at the bottom right of the pop-up card to switch to your Wiktionary dictionary.

---

## Overview & Key Features

This project addresses the strict formatting constraints, character diacritics, and undocumented limitations of Kindle dictionary lookup engines when processing multi-gigabyte dictionary dumps.

> [!IMPORTANT]
> **Language Support:** This repository is currently optimized and tested exclusively for **Latin** (handling macron stripping, vowel length variants, morphological tags, etc.) Only Latin `.mobi` files are currently published in Releases. However, the core parsing and rendering architecture is intended to be language-agnostic and can be extended to support other Wiktionary target languages.

- **Kindle Constraint Resolution:**
  - **Deterministic Lookups:** A Kindle opens only one of the labels a tapped word reaches, and when none is spelled exactly like the word, the index order decides. Every spelling therefore gets one owner: a macronized spelling only one entry has (*lātum*) opens that entry, while a spelling that reaches several entries (*latum* in an unmacronized text, or *lātus* shared by two lemmas) opens a short disambiguation card listing each candidate with its part of speech, parse, first gloss and a link. An entry whose headword a card takes keeps a numbered headword label (*latus¹*).
- **Orthography & Variant Handling:** Handles both macronized and unmacronized text (e.g., *amō* vs. *amo*): the Kindle ignores macrons and case when matching, so entries carry macronized labels only, and disputed vowel lengths (ā̆) get both spellings. Texts that write u for consonantal v (*uir*) or j for consonantal i (*jam*, *cujus*) get those spellings too, since the device does not fold them.
- **Forms Wiktionary implies:** Participles, comparatives and superlatives that have no page of their own get their regular declension, and alternative and Medieval Latin spellings without a page are indexed. Pages that only point to a lemma (an inflected form, an alternative spelling) merge into it, even when they name the lemma by its page title (*iuro* for *iūrō*).
- **What merged pages say:** A merged page that is a word of its own keeps a line in its lemma's entry, with its meaning when Wiktionary gives one: *dim.* **frīgidulus**: somewhat cold; *alt.* **voltus**. Inflected forms get no line. A comparative or superlative the headword line already names gets none either.
- **Popup-safe markup:** The lookup popup applies no stylesheet and kindling strips `class` attributes, so entries mark parts of speech and labels with `<i>` and `<b>` instead of CSS classes.
- **Memory-Efficient Processing:** Processes multi-gigabyte Kaikki JSONL files without excessive memory usage by combining streaming CLI utilities (`pigz` + `ripgrep`) with an external disk-backed merge sort (`heapq` + `orjson`).
- **Automated Builds:** Scheduled GitHub Actions run every Sunday to fetch the latest Wiktionary edits and compile fresh releases.

---

## Developer Setup & Usage

### Prerequisites
* **Python 3.10+**
* **kindling:** [`kindling-cli`](https://github.com/ciscoriordan/kindling/releases) compiles the `.mobi` (Amazon's `kindlegen` is not supported). The CLI looks for `kindling-cli` on your `PATH`; otherwise pass its path with `--kindling`. CI uses v0.45.6, checked against its SHA-256.
* *(Optional, Recommended)*: [`uv`](https://docs.astral.sh/uv/) for package management, and system utilities `ripgrep` / `pigz` for faster file extraction.

### Environment Setup

```bash
# Clone the repository
git clone [https://github.com/njand/wiktionary-to-kindle.git](https://github.com/njand/wiktionary-to-kindle.git)
cd wiktionary-to-kindle

# Sync dependencies using uv (includes optional 'fast' extras)
uv sync --all-extras

```

### Running the CLI Engine

Run the CLI tool specifying your target ISO language code:

```bash
# Download, filter, external merge-sort, and compile the Latin dictionary
uv run wiktionary-to-kindle --lang "la"

```

#### CLI Options

| Flag | Description |
| --- | --- |
| `--lang <code>` | Target ISO language code (default: `la`). |
| `--resort` | Re-runs the external merge sort. Otherwise the sorted file is cached beside the input and reused while the input is unchanged. |
| `--input <path>` | Path to a local `.jsonl` dump file, skipping automatic downloads. |
| `--no-download` | Uses the dump already in `downloads/` instead of downloading one. |
| `--kindling <path>` | Path to `kindling-cli` if it is not on your `PATH` (`--kindlegen` is the old name). |
| `--descendants <list>` | Space-separated list of descendant languages to retain in dictionary entries (default: English, Portuguese, Spanish, French, Italian). |

---

## Pipeline Architecture

`pipeline.build_dictionary` runs the stages in order; each lives in its own module of `wiktionary_to_kindle/`:

1. **Ingest** (`ingest.py`): Downloads raw Wiktionary JSONL data from Kaikki.org and extracts language-specific entries using `pigz` and `ripgrep` (or standard Python `gzip`/`json` fallbacks), keeping the dump's date.
2. **Merge** (`merge/`): A disk-backed merge sort (`heapq.merge`) puts the lemmas in order without holding the dump in memory, and folds every page that only points to a lemma into it (`pointers.py`), with generated forms (`forms.py`) and a line for merged pages that are words of their own (`related.py`). The result is cached beside the input.
3. **Lexicon model** (`models/`): Parses merged entries into `Entry`, `Header`, `Sense` and `Inflection` objects, normalizing tags.
4. **Label resolution** (`label_resolver.py`): Gives each lookup spelling one owner, an entry or a disambiguation card.
5. **Render** (`render/`): Writes entries, cards and the front page as XHTML with Jinja2 templates following Kindle's markup (`idx:entry`, `idx:orth`, `idx:infl`).
6. **Compile** (`compiler.py`): Writes the `.opf` package and runs kindling to produce the `.mobi`.

### Measuring lookup quality

```bash
# Index statistics of a build, and a comparison between two builds
uv run python -m wiktionary_to_kindle.quality stats outputs/KindleDictionary-la -o stats.json
uv run python -m wiktionary_to_kindle.quality diff old-stats.json stats.json

# How many words of real Latin texts (corpus/la.tsv) open an entry, and why the rest do not
uv run python -m wiktionary_to_kindle.quality coverage outputs/KindleDictionary-la corpus/la.tsv -o coverage

# A small, self-consistent sample of the dump for fast development builds
uv run python -m wiktionary_to_kindle.quality sample downloads/kaikki-la.jsonl downloads/sample-la.jsonl
uv run wiktionary-to-kindle --lang la --no-download --input downloads/sample-la.jsonl
```

Coverage resolves each word with the Kindle's own matching rules: case and macrons are ignored, and when several entries share a label the index order picks one ("ambiguous"). Pass `--kindling <binary> --mobi <file>` to also check the most frequent words with kindling's on-device lookup simulator. CI publishes the statistics, their change since the last release, and the coverage report in each release's notes.

---

## Contributing

Contributions are welcome. If you would like to extend support to another language (e.g., Ancient Greek, French):

1. Add any language-specific normalization or morphological tag parsing needed in `wiktionary_to_kindle/models/`.
2. Add the language code to the matrix in `.github/workflows/dictionary-build.yml`.
3. Open a PR.

---

## License & Credits

This project is open-source software licensed under the [MIT License](/LICENSE).

Dictionary data is sourced from [Wiktionary](https://www.wiktionary.org/) via the [Kaikki.org](https://kaikki.org/) machine-readable parsing project.

The dictionaries contain Wiktionary text, which is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); each dictionary is distributed under that license and opens with a page that credits Wiktionary's contributors and Kaikki.org, states the license, and gives the date of the Wiktionary data and the build. The downloader records the dump's date from Kaikki's `Last-Modified` header (`downloads/<file>.date`); for a dump passed with `--input`, put the date in `<file>.date` beside it, or the file's own date is used.
