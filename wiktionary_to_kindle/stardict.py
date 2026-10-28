"""StarDict export for GoldenDict, KOReader and other readers that are not Kindles.

kindling writes the bundle from the same OPF the .mobi is built from (`kindling stardict`):
each entry and card under its idx:orth label, its idx:iform labels as .syn redirects. Two
things then need fixing, because these readers are not Kindles:

- A card links to its entries by page and id (`0048.xhtml#29169`), which a StarDict reader
  cannot follow; the links become `bword://<label>`, the label the entry is stored under.
- A Kindle ignores macrons when matching a tapped word, so the build only indexes the
  unmacronized spelling where a card needs it. StarDict readers match more literally, so
  every label also gets its spelling without accents (`amavisti` for `amāvistī`), unless
  that spelling is already a label of its own.

StarDict format: https://github.com/huzheng001/stardict-3/blob/master/dict/doc/StarDictFileFormat
"""

import html
import re
import shutil
import struct
import subprocess
import unicodedata
from pathlib import Path

from .quality.labels import read_entries
from .utils import ABBREVIATION_MARKS, MACRON, VOWELS

OVERLINE = "̅"

HREF_PATTERN = re.compile(r'href="([^"#]*\.xhtml#[^"]*)"')


def export_stardict(kindling, files_dir, bundle_dir, description):
    """Write the StarDict bundle for files_dir/dictionary.opf into bundle_dir (its four
    files are named after the folder), fix it for StarDict readers, and zip it beside the
    folder. Return the zip's path."""
    bundle_dir = Path(bundle_dir)
    subprocess.run(
        [
            kindling,
            "stardict",
            Path(files_dir, "dictionary.opf"),
            "-o",
            bundle_dir,
            "--description",
            description,
        ],
        check=True,
    )
    labels = {e.key: e.headword for e in read_entries(files_dir)}
    Bundle.read(bundle_dir).relink(labels).add_unaccented().write()
    zip_path = shutil.make_archive(
        str(bundle_dir) + "-stardict", "zip", bundle_dir.parent, bundle_dir.name
    )
    return Path(zip_path)


def unaccented(word):
    """word without macrons, breves and other accents, keeping case and abbreviation
    signs (n̄, aͣ). æ and œ stay: they are letters a reader types as such."""
    out, base = [], ""
    for char in unicodedata.normalize("NFD", word):
        if not unicodedata.combining(char):
            base = char
        elif char not in ABBREVIATION_MARKS:
            continue
        elif char in (MACRON, OVERLINE) and base in VOWELS:
            continue  # a long vowel, not an abbreviation
        out.append(char)
    return unicodedata.normalize("NFC", "".join(out))


def stardict_key(word):
    """Sort key of StarDict's stardict_strcmp: ASCII-case-insensitive bytes, then bytes."""
    data = word.encode("utf-8")
    return data.lower(), data


class Bundle:
    """A StarDict bundle in memory: .idx words with their .dict articles, .syn redirects
    (word, index into words) and the .ifo fields."""

    def __init__(self, path, ifo, words, articles, synonyms):
        self.path = Path(path)
        self.ifo = ifo
        self.words = words
        self.articles = articles
        self.synonyms = synonyms

    @classmethod
    def read(cls, path):
        path = Path(path)
        stem = path / path.name
        lines = stem.with_suffix(".ifo").read_text(encoding="utf-8").splitlines()
        ifo = dict(line.split("=", 1) for line in lines[1:] if "=" in line)

        data = stem.with_suffix(".dict").read_bytes()
        words, articles = [], []
        for word, offset, size in _records(stem.with_suffix(".idx"), ">II"):
            words.append(word)
            articles.append(data[offset : offset + size].decode("utf-8"))
        synonyms = []
        if stem.with_suffix(".syn").exists():
            synonyms = [
                (word, index)
                for word, index in _records(stem.with_suffix(".syn"), ">I")
            ]
        return cls(path, ifo, words, articles, synonyms)

    def relink(self, labels):
        """Point links to `<page>#<id>` at bword://<label>, labels mapping the one to the
        other. A link to a page that is not in labels is left as it is."""

        def replace(match):
            label = labels.get(html.unescape(match.group(1)))
            if label is None:
                return match.group(0)
            return f'href="bword://{html.escape(label)}"'

        self.articles = [HREF_PATTERN.sub(replace, a) for a in self.articles]
        return self

    def add_unaccented(self):
        """Add the spelling without accents of every word and synonym as a synonym."""
        taken = set(self.words) | {word for word, _ in self.synonyms}
        added = {}
        pairs = [(word, i) for i, word in enumerate(self.words)] + self.synonyms
        for word, index in pairs:
            plain = unaccented(word)
            if plain not in taken:
                added.setdefault((plain, index), None)
        self.synonyms += list(added)
        return self

    def write(self):
        stem = self.path / self.path.name
        order = sorted(
            range(len(self.words)), key=lambda i: stardict_key(self.words[i])
        )
        new_index = {old: new for new, old in enumerate(order)}

        idx, data, offset = bytearray(), bytearray(), 0
        for i in order:
            article = self.articles[i].encode("utf-8")
            idx += self.words[i].encode("utf-8") + b"\0"
            idx += struct.pack(">II", offset, len(article))
            data += article
            offset += len(article)

        syn = bytearray()
        for word, index in sorted(
            self.synonyms, key=lambda s: (stardict_key(s[0]), new_index[s[1]])
        ):
            syn += word.encode("utf-8") + b"\0" + struct.pack(">I", new_index[index])

        stem.with_suffix(".idx").write_bytes(idx)
        stem.with_suffix(".dict").write_bytes(data)
        stem.with_suffix(".syn").write_bytes(syn)
        self.ifo.update(
            wordcount=str(len(self.words)),
            synwordcount=str(len(self.synonyms)),
            idxfilesize=str(len(idx)),
        )
        stem.with_suffix(".ifo").write_text(
            "StarDict's dict ifo file\n"
            + "".join(f"{key}={value}\n" for key, value in self.ifo.items()),
            encoding="utf-8",
            newline="\n",
        )


def _records(path, tail):
    """Yield (word, *numbers) from a .idx or .syn file: a NUL-terminated UTF-8 word, then
    the big-endian numbers struct format tail describes."""
    data = path.read_bytes()
    size = struct.calcsize(tail)
    pos = 0
    while pos < len(data):
        end = data.index(b"\0", pos)
        yield data[pos:end].decode("utf-8"), *struct.unpack_from(tail, data, end + 1)
        pos = end + 1 + size
