# Wiktionary to Kindle

[![Latest release](https://img.shields.io/github/v/release/njand/wiktionary-to-kindle?label=release)](https://github.com/njand/wiktionary-to-kindle/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/njand/wiktionary-to-kindle/total)](https://github.com/njand/wiktionary-to-kindle/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Free Kindle dictionaries built from Wiktionary, with StarDict versions for KOReader and GoldenDict. Press and hold a word in a Latin, Ancient Greek or Turkish book, and the dictionary opens the entry it belongs to, whatever its form or spelling.

## Download

| Language | Kindle | KOReader, GoldenDict | Status |
| --- | --- | --- | --- |
| Latin–English | [la-wiktionary.mobi](https://github.com/njand/wiktionary-to-kindle/releases/latest/download/la-wiktionary.mobi) | [StarDict](https://github.com/njand/wiktionary-to-kindle/releases/download/latest-build/la-wiktionary-stardict.zip) | Released |
| Ancient Greek–English | [grc-wiktionary.mobi](https://github.com/njand/wiktionary-to-kindle/releases/download/latest-build/grc-wiktionary.mobi) | [StarDict](https://github.com/njand/wiktionary-to-kindle/releases/download/latest-build/grc-wiktionary-stardict.zip) | In testing |
| Turkish–English | [tr-wiktionary.mobi](https://github.com/njand/wiktionary-to-kindle/releases/download/latest-build/tr-wiktionary.mobi) | [StarDict](https://github.com/njand/wiktionary-to-kindle/releases/download/latest-build/tr-wiktionary-stardict.zip) | In testing |

Each link downloads the file itself; then follow [Install on a Kindle](#install-on-a-kindle). The Latin `.mobi` is the [latest release](https://github.com/njand/wiktionary-to-kindle/releases/latest), the newest build checked on a Kindle; the other links are the [newest build](https://github.com/njand/wiktionary-to-kindle/releases/tag/latest-build), replaced every week. Older builds are on the [releases page](https://github.com/njand/wiktionary-to-kindle/releases).

The dictionaries are rebuilt every week from the latest Wiktionary data.

More languages will follow. The build is meant to work for any language Wiktionary covers well; see [Contributing](#contributing).

## What a lookup does

- **Any form opens its word.** *tulerunt* opens **ferō**, *hominibus* opens **homō**, and *amavisti* opens **amō**, including participles and comparatives that Wiktionary only implies.
- **Any spelling opens it too.** Lookups work with or without macrons, with *u* or *v*, with *i* or *j*, and with ligatures: *uirum* opens **vir**, *prœlium* opens **proelium**.
- **Nothing is hidden.** When a spelling belongs to more than one word, the popup lists all of them, likeliest first, and you swipe to the rest.
- **Entries read like a print dictionary**, with the principal parts on the headword line, numbered senses, and the etymology.

In the texts the project tests against, the dictionary opens an entry for 98.6% of the words in Cicero's first speech against Catiline, 97.7% in Book 1 of Caesar's *Gallic War*, 94.6% in Genesis in the Vulgate, and 93.4% in Book 1 of the *Aeneid*. (The release notes give a lower figure for Latin as a whole, about 86%, because the test texts also include a school edition of Caesar whose English notes count as misses.) The misses include words with *-que* attached, such as *dixitque*, which the dictionary doesn't split, and names Wiktionary doesn't list. If you can edit your book, put a hair space (U+200A) before the *-que*: a press on *dixit* then selects only *dixit* and opens **dīcō**. Zero-width and other thin spaces don't work; the Kindle selects the whole word through them.

## Ancient Greek (in testing)

The Ancient Greek–English dictionary is built the same way, from Wiktionary's Ancient Greek entries. Until it has been checked on a Kindle, it is published only in the weekly builds ([download](#download)).

A Kindle matches Greek accents, breathings and capitals exactly, so the dictionary lists every spelling a Greek text prints: without the length marks Wiktionary adds (ἀπεκρίθη opens **ἀποκρίνω**) and with the long vowels marked, as school editions print them (λῡ́ω opens **λύω**), with a grave for a final acute (καὶ opens **καί**), and capitalized for headwords and small words that start sentences (Καὶ, Οὐκ, Ταῦτα). In Perseus's editions of Homer, Herodotus, Xenophon, Plato, Lysias and the Gospel of John, it opens an entry for 91.7% of the words: 93–95% in most of them, 87.8% in Herodotus, whose Ionic forms Wiktionary often lacks.

## Turkish (in testing)

The Turkish–English dictionary is built from Wiktionary's Turkish entries. Until it has been checked on a Kindle, it is published only in the weekly builds ([download](#download)).

A Kindle ignores case and the Turkish letters' marks when it looks a word up (*KIZI* and *kizi* open **kız**), so the dictionary only has to reach the forms themselves. It lists every form in Wiktionary's tables (*evlerimizden* opens **ev**), the converbs (*gidip*, *giderken*) and the copula, *-(y)lA* and *-ki* forms texts use most (*vardır*, *nedeniyle*, *dünyadaki*). On its own it opens an entry for 88.4% of the words in a set of modern Turkish prose and Ömer Seyfettin's stories.

Turkish stacks suffixes beyond what any table lists (*evlerimizdekilerden*, "from those in our houses"), so a Turkish book reads best **prepared**: `prepare-book` puts a hair space between the stem and the suffixes of each word the dictionary cannot reach whole. A press on *ev* then opens **ev**, and a press on *lerimizdekilerden* opens an entry that explains the suffixes: *plural + our + in + the one that is + plural + from*. In the same texts, a prepared book opens an entry for 95.5% of the words, and splits 7% of them. A language model reads each sentence to choose where to split (so *gözlükçüler* splits after **gözlükçü**, not **göz**), or `--decide rooted` splits without one.

```bash
uv sync --extra segment
uv run prepare-book book.epub --kindling kindling-cli   # writes book-prepared.epub and .azw3
```

The model needs an API key and is sent the book's sentences; a novel costs roughly $10, once, since every decision is cached beside the book. Books bought from the Kindle store have DRM and can't be prepared. The [developer guide](docs/DEVELOPING.md#preparing-books-turkish) covers the key and the options.

## Install on a Kindle

1. Download your language's `.mobi` from the [table above](#download).
2. Connect your Kindle to your computer with a USB cable.
3. Open the Kindle drive and copy the file into `documents/dictionaries/`. If that folder doesn't exist, create it.
4. Eject the Kindle.
5. On the Kindle, go to **Settings → Device Options → Language and Dictionaries → Dictionaries**, tap **Latin**, and choose the Wiktionary dictionary. For Ancient Greek and Turkish, the language they appear under is still being checked.

Send to Kindle no longer accepts `.mobi` files, so the dictionary has to be copied over USB.

If another dictionary opens when you press a word, tap its name at the bottom of the popup to switch.

### Updating to a newer release

Copy the new file over the old one in `documents/dictionaries/`. The Kindle often keeps using the old copy in books where you have already looked words up, so lookups there may fail or show nothing. Either of these fixes it:

- Restart the Kindle (hold the power button and choose **Restart**).
- Open a book in another language and look up a word there with that language's dictionary. Once that entry opens, go back to your book; the updated dictionary works again.

## KOReader and GoldenDict

Download your language's StarDict file from the [table above](#download). Unzip it and copy the folder inside (`la-wiktionary`, for Latin) into `koreader/data/dict/` for KOReader, or add it to your dictionary sources in GoldenDict. Words also match without macrons, and Greek words without accents or breathings.

## Build it yourself

You'll need Python 3.10 or later, [uv](https://docs.astral.sh/uv/), and [kindling](https://github.com/ciscoriordan/kindling/releases) on your `PATH`.

```bash
uv sync --all-extras
```

```bash
uv run wiktionary-to-kindle --lang la
```

The dictionary is written to `outputs/KindleDictionary-la/`; `--lang grc` builds the Ancient Greek one and `--lang tr` the Turkish one. See the [developer guide](docs/DEVELOPING.md) for all build options, how the pipeline works, and the tools that measure lookup quality.

## Found a mistake in an entry?

Every definition, inflection and etymology in these dictionaries comes from Wiktionary. If an entry has a wrong gloss, a missing sense or a wrong principal part, please fix it on Wiktionary itself rather than reporting it here. Anyone can edit Wiktionary, and a fix there helps everyone.

1. Open the word's page on [Wiktionary](https://en.wiktionary.org/) and edit the section for your language. Page titles have no macrons or length marks: **amō** is on the page `amo`. If you're new to editing, Wiktionary's guides for [Latin](https://en.wiktionary.org/wiki/Wiktionary:About_Latin), [Ancient Greek](https://en.wiktionary.org/wiki/Wiktionary:About_Ancient_Greek) and [Turkish](https://en.wiktionary.org/wiki/Wiktionary:About_Turkish) explain how entries are laid out.
2. Wait for the next build. Kaikki.org extracts Wiktionary's data about once a week and the dictionary is rebuilt from it every Sunday, so an edit usually reaches the dictionary within one to two weeks. The dictionary's first page gives the date of the Wiktionary data it was built from.
3. Download the new release and copy it over the old file on your Kindle (see [Updating to a newer release](#updating-to-a-newer-release) if lookups stop working).

If the entry is right on Wiktionary but wrong in the dictionary, such as missing text, a garbled layout, or a word that opens the wrong entry, that's a bug here: please [report it](#contributing).

## Contributing

Bug reports are welcome in [Issues](https://github.com/njand/wiktionary-to-kindle/issues), especially words that don't open the entry you expected. Include the language, the word exactly as your book prints it, and your device (a Kindle model, KOReader or GoldenDict).

Latin, Ancient Greek and Turkish are built so far, and the pipeline is meant to work for other languages. The [developer guide](docs/DEVELOPING.md#adding-a-language) explains how to add one.

## License and credits

The code is released under the [MIT License](LICENSE).

The dictionary text comes from [Wiktionary](https://www.wiktionary.org/), extracted by [Kaikki.org](https://kaikki.org/), and is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Each dictionary opens with a page that credits Wiktionary's contributors and Kaikki.org and gives the dates of the data and the build.

The covers use lettering cropped from the [Wiktionary logo](https://commons.wikimedia.org/wiki/File:Wiktionary-logo-en-v2.svg) (by Dan Polansky after Smurrayinchester, CC BY-SA 4.0) and are set in [DejaVu Serif](https://dejavu-fonts.github.io/) (its license ships beside it). Wiktionary is a trademark of the Wikimedia Foundation; this project is not affiliated with or endorsed by it.

The texts the coverage reports measure (from The Latin Library, Project Gutenberg, Perseus, the BOUN treebank and Wikisource; see `corpus/`) are downloaded when the reports run and are not part of this repository or the dictionaries.
