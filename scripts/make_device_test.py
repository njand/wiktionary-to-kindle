"""Build a small Kindle book for checking dictionary lookups on a real device.

Each word in the list becomes a numbered line of the book with what it tests and the
entries the popup should list: every entry with a label of the same weights, the one
kindling predicts opens first, then the rest in the order kindling's index search returns
them. Tap each word
on the Kindle and report the numbers whose popup differs.

Usage:
    python scripts/make_device_test.py outputs/KindleDictionary-la \
        tests/device_words_la.tsv -o outputs/device-test [--kindling kindling-cli]
    python scripts/make_device_test.py outputs/KindleDictionary-grc \
        tests/device_words_grc.tsv --lang grc -o outputs/device-test-grc
    python scripts/make_device_test.py outputs/KindleDictionary-tr \
        tests/device_words_tr.tsv --lang tr -o outputs/device-test-tr

Writes OUT/<lang>-device-test.azw3 (copy it to the Kindle's documents/ folder) and
OUT/predictions.md (the same list, to compare the report against). --dry-run prints the
predictions and corpus frequencies without building the book.
"""

import argparse
import datetime
import html
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from wiktionary_to_kindle.languages import LANGUAGES, get_language
from wiktionary_to_kindle.quality.corpus import tokenize
from wiktionary_to_kindle.quality.kindling import default_binary, lookup
from wiktionary_to_kindle.quality.labels import build_index, read_entries
from wiktionary_to_kindle.render.cover import labelled_cover

ZWSP = "\u200b"
# A hair space: the only separator a long press stops at (device test, 2026-10-29), which
# prepare-book puts between a Turkish stem and its suffixes
HAIR = "\u200a"
SECTIONS = {
    "frequent": "Short, frequent words",
    "rare": "Long and rare words",
    "macrons": "Macrons, capitals and breves",
    "inflections": "Inflected forms",
    "spellings": "Spelling variants",
    "homographs": "Homographs with the same macrons",
    "unmacronized": "Homographs only without macrons",
    "ambiguous": "Inflected forms of several words",
    "enclitics": "Enclitics after a zero-width space",
    # Turkish
    "dotted": "Dotted and dotless i",
    "generated": "Forms the dictionary generates",
    "names": "Names with an apostrophe",
    "splits": "Words split with a hair space",
    "passage": "Running text, split words free to break",
    "passage-nowrap": "The same text, split words kept on one line",
    # Ancient Greek
    "capitals": "Capitals",
    "accents": "Grave, enclitic and other accents",
    "encodings": "Accents encoded another way",
    "elision": "Elision marks",
    "length": "Words Wiktionary writes with length marks",
    "letters": "Breathings, iota subscripts and other letters",
}
# ύ in a word of the list stands for that character: oxia and tonos look alike
ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


def read_words(path):
    words = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            section, word, note = line.split("\t")
            word = ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), word)
            word = word.replace("{zwsp}", ZWSP).replace("{hair}", HAIR)
            words.append((section, word, note))
    return sorted(words, key=lambda w: list(SECTIONS).index(w[0]))


def predict(index, kindling, mobi, word, section):
    """The entries the popup lists for a tapped word: 'fēmina (noun) / femur (noun)'.

    The one kindling resolves comes first, then the rest in the order kindling's index
    search returns their labels (the device lists them so: nōnae's Non. before nōn). A word
    split with hair spaces gets a prediction for each part; a passage gets none."""
    if section.startswith("passage"):
        return ""
    if HAIR in word:
        return "; ".join(
            f"tap “{part}”: {predict(index, kindling, mobi, part, section)}"
            for part in word.split(HAIR)
        )
    tapped = word.split(ZWSP)[0]  # what a zero-width space should leave selected
    run = index.run(tapped)
    if not run:
        return "nothing opens"
    result = lookup(kindling, mobi, tapped)
    by_label = {label: entry for label, entry in run}
    order = [result["label"]] + result["labels"]
    ranked = [by_label[label] for label in order if label in by_label]
    # Labels kindling did not list (none should be missing) keep their page order
    entries = {entry.key: entry for entry in ranked + [entry for _, entry in run]}
    return " / ".join(f"{entry.headword} ({entry.pos})" for entry in entries.values())


def corpus_counts(cache_dir):
    counts = Counter()
    for path in Path(cache_dir).glob("*.txt"):
        counts.update(tokenize(path.read_text(encoding="utf-8")))
    return counts


def write_book(out_dir, rows, built, language):
    """Write the book's XHTML, OPF and cover into out_dir.

    The build time is in the title, identifier and cover, so the Kindle files each build
    as a new book and a stale copy is easy to tell apart."""
    name, code = language.name, language.code
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(out_dir, "cover.png").write_bytes(
        labelled_cover("Device test", [f"{name} dictionary", built])
    )
    body = [
        f"<h1>{name} dictionary: device test</h1>",
        f"<p><small>Built {built}.</small></p>",
        (
            f"<p>Set the Wiktionary {name} dictionary as the {name} dictionary, then "
            "press and hold each word in bold. Under it are the entries the popup should list "
            "(headword and part of speech), in the order it should list them. Write "
            "down the number of every word whose popup differs, and what it showed.</p>"
        ),
        (
            "<p>Layout: in the popup of any word, is the headword larger than the text "
            "after it? Are the etymology and descendants smaller than the definitions, "
            "and are they grey? Does every letter show, in the book and in the popup, "
            "with no empty boxes?</p>"
        ),
        (
            "<p>Report: the Kindle model and firmware (Settings, Device Info), then each "
            "number that differs, for example “12: also listed latus (noun)”.</p>"
        ),
    ]
    section = None
    for number, (sec, word, note, expected) in enumerate(rows, 1):
        if sec != section:
            section = sec
            body.append(f"<h2>{html.escape(SECTIONS[sec])}</h2>")
        if sec.startswith("passage"):
            body.append(
                f'<p id="w{number}">{number}. <small>{html.escape(note)}</small></p>'
                f'<p lang="{code}">{passage(word, sec == "passage-nowrap")}</p>'
            )
            continue
        body.append(
            f'<p id="w{number}">{number}. <b><span lang="{code}">{html.escape(word)}</span></b>'
            f"<br/><small>{html.escape(note)}</small>"
            f"<br/><small>Expect: {html.escape(expected)}</small></p>"
        )
    Path(out_dir, "test.xhtml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" lang="{code}" xml:lang="{code}">\n'
        '<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>'
        f"<title>{name} dictionary device test {built}</title></head>\n<body>\n"
        + "\n".join(body)
        + "\n</body>\n</html>\n",
        encoding="utf-8",
    )
    stamp = built.replace(" ", "-").replace(":", "")
    Path(out_dir, "test.opf").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>{name} dictionary device test {built}</dc:title>
<dc:language>{code}</dc:language>
<dc:creator>wiktionary-to-kindle</dc:creator>
<dc:identifier id="bookid">{code}-dictionary-device-test-{stamp}</dc:identifier>
<meta name="cover" content="cover-image"/>
</metadata>
<manifest>
<item id="cover-image" href="cover.png" media-type="image/png"/>
<item id="test" href="test.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="test"/></spine>
</package>
""",
        encoding="utf-8",
    )


def passage(text, nowrap):
    """A passage as markup: with nowrap, each word with a hair space in a span that keeps
    it on one line (the book's own style; kindling strips it only from dictionaries)."""
    words = []
    for word in text.split(" "):
        word = html.escape(word)
        if nowrap and HAIR in word:
            word = f'<span style="white-space: nowrap">{word}</span>'
        words.append(word)
    return " ".join(words)


def write_predictions(path, rows):
    lines = [
        "| # | Word | Tests | Expect | On device |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for number, (_sec, word, note, expected) in enumerate(rows, 1):
        shown = word.replace(ZWSP, "{zwsp}").replace(HAIR, "{hair}")
        lines.append(f"| {number} | {shown} | {note} | {expected} | |")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dict_dir", type=Path, help="e.g. outputs/KindleDictionary-la")
    parser.add_argument("words", type=Path)
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("outputs/device-test")
    )
    parser.add_argument("--kindling", default=default_binary())
    parser.add_argument("--lang", default="la", choices=sorted(LANGUAGES))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    language = get_language(args.lang)

    index = build_index(read_entries(args.dict_dir / "files"))
    mobi = next(args.dict_dir.glob("*.mobi"))
    rows = [
        (section, word, note, predict(index, args.kindling, mobi, word, section))
        for section, word, note in read_words(args.words)
    ]

    if args.dry_run:
        counts = corpus_counts("corpus/cache")
        for number, (section, word, _note, expected) in enumerate(rows, 1):
            tapped = word.split(ZWSP)[0].replace(HAIR, "|")[:40]
            print(f"{number:3} {section:12} {tapped:20} {counts[tapped]:6}  {expected}")
        return 0

    built = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    write_book(args.output / "book", rows, built, language)
    write_predictions(args.output / "predictions.md", rows)
    book = (args.output / f"{language.code}-device-test.azw3").resolve()
    subprocess.run(
        [args.kindling, "build", "test.opf", "-o", str(book)],
        cwd=args.output / "book",
        check=True,
    )
    print(f"Wrote {args.output / book.name} ({len(rows)} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
