# Wiktionary-to-Kindle

[![Build and Release Dictionaries](https://github.com/njand/wiktionary-to-kindle/actions/workflows/dictionary-build.yml/badge.svg)](https://github.com/njand/wiktionary-to-kindle/actions/workflows/dictionary-build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Python parser and rendering engine that converts large-scale [Kaikki](https://kaikki.org/) Wiktionary JSONL dumps into fully functional Kindle dictionaries (`.mobi`).

> [!TIP]
> **Looking to install a dictionary on your Kindle?**  
> If you just want to use the dictionaries on a device, you do not need to build the project from source. Download pre-compiled `.mobi` files directly from **[GitHub Releases](https://github.com/njand/wiktionary-to-kindle/releases/latest)**.

---

## Overview & Key Features

Building reliable Kindle dictionaries from raw Wiktionary dumps requires handling Kindle format quirks, character diacritics, and memory limits when processing multi-gigabyte files.

- **Kindle Constraint Resolution:**
  - **Inflection Chunking:** Kindle silently drops entries that attach too many inflections. The engine automatically splits entries exceeding 200 inflected forms into multiple index chunks while preserving full lookup coverage.
  - **Ambiguous Form Resolution:** Kindle's lookup mechanism often fails on ambiguous inflections (distinct words sharing identical inflected spellings). The parser detects these collisions and synthesizes dedicated, standalone inflection entries.
- **Orthography & Variant Handling:** Automatically handles macronized and unmacronized text (e.g., *amō* vs. *amo*), resolves disputed vowel lengths, and generates orthographic variants so search lookups succeed under standard or diacritic-heavy input.
- **Memory-Efficient Processing:** Processes multi-gigabyte Kaikki JSONL files without excessive memory usage by combining streaming CLI utilities (`pigz` + `ripgrep`) with an external disk-backed merge sort (`heapq` + `orjson`).
- **Automated Builds:** Scheduled GitHub Actions run every Sunday to fetch the latest Wiktionary edits and compile fresh releases.
- **Extensible:** Highly optimized for Latin (handling macron stripping, morphological tags, and descendant trees), but designed to process any target language code supported by Kaikki.

---

## Installation & Prerequisites

### Prerequisites
* **Python 3.10+**
* **KindleGen Binary:** Amazon's `kindlegen` (or `kindling-cli`) is required for MOBI compilation. The tool automatically searches your system `PATH` and common installation directories.
* *(Optional, Recommended)*: [`uv`](https://docs.astral.sh/uv/) for package management, and system utilities `ripgrep` / `pigz` for faster file extraction.

### Setup

```bash
# Clone the repository
git clone [https://github.com/njand/wiktionary-to-kindle.git](https://github.com/njand/wiktionary-to-kindle.git)
cd wiktionary-to-kindle

# Sync dependencies using uv (includes optional 'fast' extras)
uv sync --all-extras

```

---

## Usage

Run the CLI tool specifying your target ISO language code:

```bash
# Download, filter, external merge-sort, and compile the Latin dictionary
uv run wiktionary-to-kindle --lang "la" --sort

```

### CLI Options

| Flag | Description |
| --- | --- |
| `--lang <code>` | **Required.** Target ISO language code (e.g., `la`, `fr`, `grc`). |
| `--sort` | Executes an external disk merge-sort on the filtered JSONL before dictionary generation. |
| `--input <path>` | Path to a local `.jsonl` dump file, skipping automatic downloads. |
| `--no-download` | Disables automatic download of Kaikki raw dumps. |
| `--kindlegen <path>` | Explicit path to the `kindlegen` binary if not in system `PATH`. |
| `--descendants <list>` | Space-separated list of descendant languages to retain in dictionary entries (default: English, Portuguese, Spanish, French, Italian). |

---

## Pipeline Architecture

1. **Download & Filter:** Downloads raw Wiktionary JSONL data from Kaikki.org and extracts language-specific entries using `pigz` and `ripgrep` (or standard Python `gzip`/`json` fallbacks).
2. **External Merge Sort:** Performs a disk-backed merge sort via `heapq.merge` to group lemmas with their inflections sequentially without thrashing system memory.
3. **Data Modeling:** Parses raw entries into structured Python models (`Entry`, `Header`, `Sense`, `Inflection`), normalizing tags and resolving cross-references.
4. **XHTML Rendering:** Renders dictionary pages using Jinja2 templates following Kindle XML specifications (`idx:entry`, `idx:orth`, `idx:infl`).
5. **Compilation:** Generates the `.opf` package index and invokes `kindlegen` to produce the finalized `.mobi` file.

---

## Contributing

Contributions are welcome. To add default support for a new language:

1. Add the language code to the matrix in `.github/workflows/dictionary-build.yml`.
2. Submit a PR with any language-specific normalization logic or morphological tag overrides needed in `wiktionary_to_kindle/models/`.

---

## License & Credits

This project is open-source software licensed under the [MIT License](main/LICENSE).

Dictionary data is sourced from [Wiktionary](https://www.wiktionary.org/) via the [Kaikki.org](https://kaikki.org/) machine-readable parsing project.
