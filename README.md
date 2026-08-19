# Wiktionary-to-Kindle

[![Build and Release Dictionaries](https://github.com/njand/wiktionary-to-kindle/actions/workflows/dictionary-build.yml/badge.svg)](https://github.com/njand/wiktionary-to-kindle/actions/workflows/dictionary-build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Converts large-scale Wiktionary JSONL dumps into formatted and functional Kindle dictionaries. 

## ✨ Key Features

This project was built to address the severe formatting constraints and undocumented limitations of Kindle dictionaries, offering unparalleled lookup accuracy.

*   **Weekly Auto-Releases:** The repository runs an automated GitHub Action every Sunday, scraping the latest Wiktionary edits and compiling fresh `.mobi` dictionaries. **[👉 Download the latest up-to-date dictionary release here!](https://github.com/njand/wiktionary-to-kindle/releases/latest)**
*   **Smart Orthography & Diacritics:** Fully supports both macronized (e.g., *amō*) and unmacronized (e.g., *amo*) text. It actively resolves and generates variants for disputed vowel lengths so your lookups never fail.
*   **Overcoming Kindle's Undocumented Limitations:**
    *   **Max Inflection Limits:** Kindle silently drops dictionary entries that contain too many inflected forms. This engine intelligently duplicates and chunks massive entries (with different inflections) across split entries to guarantee 100% lookup coverage.
    *   **Ambiguous Form Resolution:** Kindle has an undocumented bug where ambiguous forms (two distinct words that share an identically spelled inflection) fail to display properly. I solve this by automatically synthesizing separate, standalone head forms for ambiguous inflections.
*   **Extensible Language Support:** Currently heavily optimized for **Latin** (handling Latin-specifc morphological tags and macrons), but the core engine is fully extensible and can be easily adapted to support other languages hosted on Wiktionary.
*   **Fast Extraction:** Leverages fast CLI tools (`ripgrep` + `pigz`) and external merge-sorting to process massive multi-gigabyte Kaikki JSONL dumps without thrashing your system's memory.

---

## 🚀 Installation & Usage

### Prerequisites
*   **Python 3.10+**
*   **KindleGen**: You must have Amazon's `kindlegen` executable. The script searches your system `PATH` and common installation directories automatically.
*   *(Optional but Recommended)*: `uv` for fast dependency management, and `ripgrep` / `pigz` for faster JSONL extraction.

### Local Setup

I recommend using [uv](https://docs.astral.sh/uv/) for environment management:

```bash
# Clone the repository
git clone https://github.com/njand/wiktionary-to-kindle.git
cd wiktionary-to-kindle

# Sync dependencies (including the 'fast' extras for orjson)
uv sync --all-extras
```

### Building a Dictionary

Run the CLI tool, specifying the target language. The engine will automatically download the latest [Kaikki raw dump](https://kaikki.org/), filter it, sort it, and compile the `.mobi` dictionary.

```bash
# Build the Latin dictionary (with external merge sorting enabled for performance)
uv run wiktionary-to-kindle --lang "la" --sort
```

#### Additional Options
*   `--input <path>`: Skip the download and use a local `.jsonl` dump.
*   `--kindlegen <path>`: Manually specify the path to your `kindlegen` binary if it cannot be found automatically.
*   `--no-download`: Force the use of local files only.

---

## 🏗️ Architecture

1.  **Downloader:** Fetches raw Wiktionary extract data from Kaikki.org.
2.  **Filter & Sort:** Extracts the target language and performs an external merge-sort to group root words and their descendants sequentially.
3.  **Parser (Models):** Converts JSON into highly structured `Entry`, `Sense`, `Header`, and `Inflection` objects, evaluating morphological tags and grammatical hierarchies.
4.  **Renderer:** Uses `Jinja2` templates to dynamically generate standard Kindle `.xhtml` pages, optimizing for reading layout, etymology trees, and descendant tracking.
5.  **Compiler:** Packages everything into an `.opf` index and leverages `kindlegen` to produce a finalized `.mobi` file.

---

## 🤝 Contributing

Contributions are welcome! If you'd like to extend support to another language (e.g., Ancient Greek, French), simply add the language code to the `.github/workflows/dictionary-build.yml` build matrix, and submit a PR with any language-specific normalization logic needed.

## 📜 License & Credits

This project relies on data extracted from [Wiktionary](https://www.wiktionary.org/) via the [Kaikki.org](https://kaikki.org/) machine-readable dictionary project.