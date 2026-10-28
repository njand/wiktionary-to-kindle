"""Build a small Kindle book for checking dictionary lookups on a real device.

Each word in the list becomes a numbered line of the book with what it tests and what
kindling's simulator predicts the tap opens (an entry, a card listing several entries, or
nothing). Tap each word on the Kindle and report the numbers whose popup differs.

Usage:
    python scripts/make_device_test.py outputs/KindleDictionary-la \
        tests/device_words_la.tsv -o outputs/device-test [--kindling kindling-cli]

Writes OUT/la-device-test.azw3 (copy it to the Kindle's documents/ folder) and
OUT/predictions.md (the same list, to compare the report against). --dry-run prints the
predictions and corpus frequencies without building the book.
"""

import argparse
import html
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from wiktionary_to_kindle.quality.corpus import tokenize
from wiktionary_to_kindle.quality.kindling import default_binary, lookup
from wiktionary_to_kindle.quality.labels import (
    ENTRY_PATTERN,
    ORTH_PATTERN,
    read_entries,
)
from wiktionary_to_kindle.utils import TEMPLATES

ZWSP = "\u200b"
SUPERSCRIPTS = str.maketrans("", "", "⁰¹²³⁴⁵⁶⁷⁸⁹")
CARD_ROW = re.compile(r"<li><a [^>]*><b>([^<]*)</b></a> <i>([^<]*)</i>")
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
}


def read_words(path):
    words = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            section, word, note = line.split("\t")
            words.append((section, word.replace("{zwsp}", ZWSP), note))
    return sorted(words, key=lambda w: list(SECTIONS).index(w[0]))


def describe_owners(files_dir):
    """Map each label to what it opens: 'card: ferō, lātus, ...' or 'lātus (adj)'."""
    cards = {}
    for page in Path(files_dir).glob("card-*.xhtml"):
        for entry_id, body in ENTRY_PATTERN.findall(page.read_text(encoding="utf-8")):
            rows = [f"{html.unescape(h)} ({pos})" for h, pos in CARD_ROW.findall(body)]
            orth = html.unescape(ORTH_PATTERN.search(body).group(1))
            cards[orth] = "card: " + ", ".join(rows)

    owners = defaultdict(list)
    for entry in read_entries(files_dir):
        if entry.is_card:
            description = cards[entry.headword]
        else:
            description = f"{entry.headword.translate(SUPERSCRIPTS)} ({entry.pos})"
        for label in dict.fromkeys(entry.labels):
            owners[label].append(description)
    return owners


def predict(kindling, mobi, owners, word):
    tapped = word.split(ZWSP)[0]  # what a zero-width space should leave selected
    result = lookup(kindling, mobi, tapped)
    if not result["opens"]:
        return "nothing opens"
    return " / ".join(owners.get(result["label"], [f"label {result['label']}"]))


def corpus_counts(cache_dir):
    counts = Counter()
    for path in Path(cache_dir).glob("*.txt"):
        counts.update(tokenize(path.read_text(encoding="utf-8")))
    return counts


def write_book(out_dir, rows):
    """Write the book's XHTML and OPF, with the dictionary's cover, into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(out_dir, "cover.png").write_bytes(TEMPLATES.joinpath("cover.png").read_bytes())
    body = [
        "<h1>Latin dictionary: device test</h1>",
        (
            "<p>Set the Wiktionary Latin dictionary as the Latin dictionary, then press and "
            "hold each word in bold. Under it is what kindling predicts the popup shows: one "
            "entry (headword and part of speech), or a card listing several entries. "
            "Write down the number of every word whose popup differs, and what it showed.</p>"
        ),
        (
            "<p>Report: the Kindle model and firmware (Settings, Device Info), then each "
            "number that differs, for example “12: opened lātus (adj), not the card”. Also "
            "say whether the card links open their entries (try a few).</p>"
        ),
    ]
    section = None
    for number, (sec, word, note, expected) in enumerate(rows, 1):
        if sec != section:
            section = sec
            body.append(f"<h2>{html.escape(SECTIONS[sec])}</h2>")
        body.append(
            f'<p id="w{number}">{number}. <b><span lang="la">{html.escape(word)}</span></b>'
            f"<br/><small>{html.escape(note)}</small>"
            f"<br/><small>Expect: {html.escape(expected)}</small></p>"
        )
    Path(out_dir, "test.xhtml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="la" xml:lang="la">\n'
        '<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>'
        "<title>Latin dictionary device test</title></head>\n<body>\n"
        + "\n".join(body)
        + "\n</body>\n</html>\n",
        encoding="utf-8",
    )
    Path(out_dir, "test.opf").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Latin dictionary device test</dc:title>
<dc:language>la</dc:language>
<dc:creator>wiktionary-to-kindle</dc:creator>
<dc:identifier id="bookid">latin-dictionary-device-test</dc:identifier>
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


def write_predictions(path, rows):
    lines = [
        "| # | Word | Tests | Expect | On device |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for number, (_sec, word, note, expected) in enumerate(rows, 1):
        shown = word.replace(ZWSP, "{zwsp}")
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
    parser.add_argument(
        "--mobi", type=Path, help="default: DICT_DIR/la-wiktionary.mobi"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    mobi = args.mobi or args.dict_dir / "la-wiktionary.mobi"
    owners = describe_owners(args.dict_dir / "files")
    rows = [
        (section, word, note, predict(args.kindling, mobi, owners, word))
        for section, word, note in read_words(args.words)
    ]

    if args.dry_run:
        counts = corpus_counts("corpus/cache")
        for number, (section, word, _note, expected) in enumerate(rows, 1):
            tapped = word.split(ZWSP)[0]
            print(f"{number:3} {section:12} {tapped:20} {counts[tapped]:6}  {expected}")
        return 0

    write_book(args.output / "book", rows)
    write_predictions(args.output / "predictions.md", rows)
    book = (args.output / "la-device-test.azw3").resolve()
    subprocess.run(
        [args.kindling, "build", "test.opf", "-o", str(book)],
        cwd=args.output / "book",
        check=True,
    )
    print(f"Wrote {args.output / 'la-device-test.azw3'} ({len(rows)} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
