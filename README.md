# Wiktionary to Kindle

[![Latest release](https://img.shields.io/github/v/release/njand/wiktionary-to-kindle?label=release)](https://github.com/njand/wiktionary-to-kindle/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/njand/wiktionary-to-kindle/total)](https://github.com/njand/wiktionary-to-kindle/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Free Kindle dictionaries built from Wiktionary. Press and hold a word in a Latin or Ancient Greek book, and the dictionary opens the entry it belongs to, whatever its form or spelling.

<!--
  Screenshot of the lookup popup goes here, for example:
  <p align="center"><img src="docs/images/popup.png" alt="The dictionary's popup on a Kindle, open on amō" width="420"></p>
-->

**[Download the latest release](https://github.com/njand/wiktionary-to-kindle/releases/latest)**

| Language | Status | File |
| --- | --- | --- |
| Latin–English | Released | `la-wiktionary.mobi` |
| Ancient Greek–English | In testing, in the weekly [pre-releases](https://github.com/njand/wiktionary-to-kindle/releases) | `grc-wiktionary.mobi` |
| Turkish–English | In development | |

More languages will follow. The build is meant to work for any language Wiktionary covers well; see [Contributing](#contributing).

## What a lookup does

- **Any form opens its word.** *tulerunt* opens **ferō**, *hominibus* opens **homō**, and *amavisti* opens **amō**, including participles and comparatives that Wiktionary only implies.
- **Any spelling opens it too.** Lookups work with or without macrons, with *u* or *v*, with *i* or *j*, and with ligatures: *uirum* opens **vir**, *prœlium* opens **proelium**.
- **Nothing is hidden.** When a spelling belongs to more than one word, the popup lists all of them, likeliest first, and you swipe to the rest.
- **Entries read like a print dictionary**, with the principal parts on the headword line, numbered senses, and the etymology.

In the texts the project tests against, the dictionary opens an entry for 98.6% of the words in Cicero's first speech against Catiline, 97.6% in Book 1 of Caesar's *Gallic War*, 94.6% in Genesis in the Vulgate, and 93.2% in Book 1 of the *Aeneid*. The misses include words with *-que* attached, such as *dixitque*, which the dictionary doesn't split, and names Wiktionary doesn't list. If you can edit your book, put a hair space (U+200A) before the *-que*: a press on *dixit* then selects only *dixit* and opens **dīcō**. Zero-width and other thin spaces don't work; the Kindle selects the whole word through them.

The dictionaries are rebuilt every week from the latest Wiktionary data.

## Ancient Greek (in testing)

The Ancient Greek–English dictionary is built the same way, from Wiktionary's Ancient Greek entries. Until it has been checked on a Kindle, it is published only in the weekly [pre-releases](https://github.com/njand/wiktionary-to-kindle/releases).

A Kindle matches Greek accents, breathings and capitals exactly, so the dictionary lists every spelling a Greek text prints: without the length marks Wiktionary adds (ἀπεκρίθη opens **ἀποκρίνω**) and with the long vowels marked, as school editions print them (λῡ́ω opens **λύω**), with a grave for a final acute (καὶ opens **καί**), and capitalized for headwords and small words that start sentences (Καὶ, Οὐκ, Ταῦτα). In Perseus's editions of Homer, Herodotus, Xenophon, Plato, Lysias and the Gospel of John, it opens an entry for 91.7% of the words: 93–95% in most of them, 87.8% in Herodotus, whose Ionic forms Wiktionary often lacks.

## Turkish (in development)

Turkish builds words by stacking suffixes (*evlerimizdeydi*, "it was in our houses"), so most of the forms in a Turkish book appear in no inflection table. The work under way teaches the dictionary to reach them; the [roadmap](ROADMAP.md) has the plan and the measurements so far.

## Install on a Kindle

1. Download `la-wiktionary.mobi` from the [latest release](https://github.com/njand/wiktionary-to-kindle/releases/latest) (or `grc-wiktionary.mobi` from a pre-release, for Ancient Greek).
2. Connect your Kindle to your computer with a USB cable.
3. Open the Kindle drive and copy the file into `documents/dictionaries/`. If that folder doesn't exist, create it.
4. Eject the Kindle.
5. On the Kindle, go to **Settings → Device Options → Language and Dictionaries → Dictionaries**, tap **Latin**, and choose the Wiktionary dictionary. Under which language a Kindle lists the Ancient Greek dictionary is still being checked.

Send to Kindle no longer accepts `.mobi` files, so the dictionary has to be copied over USB.

If another dictionary opens when you press a word, tap its name at the bottom of the popup to switch.

## KOReader and GoldenDict

Each release also includes `la-wiktionary-stardict.zip` (and `grc-wiktionary-stardict.zip` for Ancient Greek). Unzip it and copy the `la-wiktionary` folder into `koreader/data/dict/` for KOReader, or add it to your dictionary sources in GoldenDict. Words also match without macrons, and Greek words without accents or breathings.

## Build it yourself

You'll need Python 3.10 or later, [uv](https://docs.astral.sh/uv/), and [kindling](https://github.com/ciscoriordan/kindling/releases) on your `PATH`.

```bash
uv sync --all-extras
```

```bash
uv run wiktionary-to-kindle --lang la
```

The dictionary is written to `outputs/KindleDictionary-la/`; `--lang grc` builds the Ancient Greek one. See the [developer guide](docs/DEVELOPING.md) for all build options, how the pipeline works, and the tools that measure lookup quality.

## Found a mistake in an entry?

Every definition, inflection and etymology in these dictionaries comes from Wiktionary. If an entry has a wrong gloss, a missing sense or a wrong principal part, please fix it on Wiktionary itself rather than reporting it here. Anyone can edit Wiktionary, and a fix there helps everyone who uses it, not only readers of this dictionary.

1. Open the word's page on [Wiktionary](https://en.wiktionary.org/) and edit the section for your language. Page titles have no macrons or length marks: **amō** is on the page `amo`. If you're new to editing, Wiktionary's guides for [Latin](https://en.wiktionary.org/wiki/Wiktionary:About_Latin) and [Ancient Greek](https://en.wiktionary.org/wiki/Wiktionary:About_Ancient_Greek) explain how entries are laid out.
2. Wait for the next release. Wiktionary's data is published every couple of weeks and the dictionary is rebuilt from it weekly, so an edit usually reaches the dictionary within two to three weeks. The dictionary's first page gives the date of the Wiktionary data it was built from.
3. Download the new release and copy it over the old file on your Kindle.

If the entry is right on Wiktionary but wrong in the dictionary, such as missing text, a garbled layout, or a word that opens the wrong entry, that's a bug here: please report it (see below).

## Contributing

Bug reports are welcome, especially words that don't open the entry you expected. Include the word as it appears in your book.

Latin and Ancient Greek are built so far, Turkish is under way, and the pipeline is meant to work for other languages. The [developer guide](docs/DEVELOPING.md#adding-a-language) explains how to add one.

## License and credits

The code is released under the [MIT License](LICENSE).

The dictionary text comes from [Wiktionary](https://www.wiktionary.org/), extracted by [Kaikki.org](https://kaikki.org/), and is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Each dictionary opens with a page that credits Wiktionary's contributors and Kaikki.org and gives the dates of the data and the build.
