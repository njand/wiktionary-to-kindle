"""What a tap on each spelling opens in a built dictionary, read back from its pages, for
prepare-book: which words need a split, and which splits leave a stem that opens.

Reading every page takes a while, so the result is cached beside the dictionary
(lexicon.json.gz), and rebuilt when the pages change.
"""

import gzip
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..quality.labels import (
    ENTRY_PATTERN,
    IFORM_PATTERN,
    ORTH_PATTERN,
    POS_PATTERN,
    _pos_code,
)
from ..render.shared_labels import unmark
from ..utils import kindle_fold

CACHE_NAME = "lexicon.json.gz"
LEXICON_VERSION = 1
FIRST_GLOSS = re.compile(r"<li>(.*?)(?:</li>|<ol>)", re.DOTALL)


@dataclass(frozen=True)
class Sense:
    """An entry a tap reaches: its headword, part of speech and first gloss."""

    headword: str
    pos: str | None
    gloss: str

    def describe(self):
        pos = f" ({self.pos})" if self.pos else ""
        gloss = f": {self.gloss}" if self.gloss else ""
        return f"{self.headword}{pos}{gloss}"


class Lexicon:
    def __init__(self, entries, by_fold):
        self.entries = entries  # [Sense]
        self.by_fold = by_fold  # folded spelling -> [index into entries]

    def lookup(self, word):
        """The entries a tap on word reaches, in stored order, each once."""
        found = dict.fromkeys(self.by_fold.get(kindle_fold(word), []))
        return [self.entries[i] for i in found]

    def opens(self, word):
        return kindle_fold(word) in self.by_fold

    @classmethod
    def load(cls, dict_dir):
        """The lexicon of a built dictionary (outputs/KindleDictionary-tr)."""
        pages = sorted(Path(dict_dir, "files").glob("*.xhtml"))
        stamp = [[p.name, p.stat().st_size, p.stat().st_mtime_ns] for p in pages]
        cache = Path(dict_dir, CACHE_NAME)
        if cache.exists():
            with gzip.open(cache, "rt", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") == LEXICON_VERSION and data.get("pages") == stamp:
                return cls([Sense(*e) for e in data["entries"]], data["by_fold"])
        entries, by_fold = [], {}
        for page in pages:
            text = page.read_text(encoding="utf-8")
            for _entry_id, body in ENTRY_PATTERN.findall(text):
                orth = ORTH_PATTERN.search(body)
                labels = [html.unescape(orth.group(1))] if orth else []
                labels += [html.unescape(v) for v in IFORM_PATTERN.findall(body)]
                if not labels:
                    continue
                gloss = FIRST_GLOSS.search(body)
                gloss = (
                    html.unescape(re.sub(r"<[^>]+>", "", gloss.group(1)))
                    if gloss
                    else ""
                )
                index = len(entries)
                entries.append(
                    Sense(
                        unmark(labels[0]),
                        _pos_code(POS_PATTERN.search(body)),
                        gloss.strip()[:120],
                    )
                )
                for label in dict.fromkeys(labels):
                    by_fold.setdefault(kindle_fold(label), []).append(index)
        tmp = cache.with_suffix(".part")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(
                {
                    "version": LEXICON_VERSION,
                    "pages": stamp,
                    "entries": [[e.headword, e.pos, e.gloss] for e in entries],
                    "by_fold": by_fold,
                },
                f,
                ensure_ascii=False,
            )
        tmp.replace(cache)
        return cls(entries, by_fold)
