# Wiktionary to Kindle

[![Latest release](https://img.shields.io/github/v/release/njand/wiktionary-to-kindle?label=release)](https://github.com/njand/wiktionary-to-kindle/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/njand/wiktionary-to-kindle/total)](https://github.com/njand/wiktionary-to-kindle/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A free Latin–English dictionary for Kindle, built from Wiktionary. Press and hold a word in any Latin book, and the dictionary opens the entry it belongs to, whatever its form or spelling.

<!--
  Screenshot of the lookup popup goes here, for example:
  <p align="center"><img src="docs/images/popup.png" alt="The dictionary's popup on a Kindle, open on amō" width="420"></p>
-->

**[Download the latest release](https://github.com/njand/wiktionary-to-kindle/releases/latest)**

## What a lookup does

| You tap | The popup opens |
| --- | --- |
| *amavisti* | **amō**, to love |
| *tulerunt* | **ferō**, to bear, to carry |
| *uirum* | **vir**, man |
| *hominibus* | **homō**, human, person, man |
| *prœlium* | **proelium**, battle |
| *non* | **nōn**, not |

Inflected forms lead to their lemma, including participles and comparatives that Wiktionary only implies. Lookups work with or without macrons, with *u* or *v*, and with *i* or *j*. When a spelling belongs to more than one word, the popup lists all of them, with the likeliest first.

Each entry is laid out like a print dictionary, with the principal parts on the headword line, numbered senses, and the etymology.

In the texts the project tests against, the dictionary opens an entry for 98.6% of the words in Cicero's first speech against Catiline, 97.6% in Book 1 of Caesar's *Gallic War*, 94.6% in Genesis in the Vulgate, and 93.2% in Book 1 of the *Aeneid*. The misses include words with *-que* attached, such as *dixitque*, which the dictionary doesn't split, and names Wiktionary doesn't list.

The dictionary is rebuilt every week from the latest Wiktionary data.

## Install on a Kindle

1. Download `la-wiktionary.mobi` from the [latest release](https://github.com/njand/wiktionary-to-kindle/releases/latest).
2. Connect your Kindle to your computer with a USB cable.
3. Open the Kindle drive and copy the file into `documents/dictionaries/`. If that folder doesn't exist, create it.
4. Eject the Kindle.
5. On the Kindle, go to **Settings → Device Options → Language and Dictionaries → Dictionaries**, tap **Latin**, and choose the Wiktionary dictionary.

Send to Kindle no longer accepts `.mobi` files, so the dictionary has to be copied over USB.

If another dictionary opens when you press a word, tap its name at the bottom of the popup to switch.

## KOReader and GoldenDict

Each release also includes `la-wiktionary-stardict.zip`. Unzip it and copy the `la-wiktionary` folder into `koreader/data/dict/` for KOReader, or add it to your dictionary sources in GoldenDict.

## Build it yourself

You'll need Python 3.10 or later, [uv](https://docs.astral.sh/uv/), and [kindling](https://github.com/ciscoriordan/kindling/releases) on your `PATH`.

```bash
uv sync --all-extras
```

```bash
uv run wiktionary-to-kindle --lang la
```

The dictionary is written to `outputs/KindleDictionary-la/`. See the [developer guide](docs/DEVELOPING.md) for all build options, how the pipeline works, and the tools that measure lookup quality.

## Contributing

Bug reports are welcome, especially words that don't open the entry you expected. Include the word as it appears in your book.

Only Latin is built so far, but the pipeline is meant to work for other languages. The [developer guide](docs/DEVELOPING.md#adding-a-language) explains how to add one.

## License and credits

The code is released under the [MIT License](LICENSE).

The dictionary text comes from [Wiktionary](https://www.wiktionary.org/), extracted by [Kaikki.org](https://kaikki.org/), and is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Each dictionary opens with a page that credits Wiktionary's contributors and Kaikki.org and gives the dates of the data and the build.
