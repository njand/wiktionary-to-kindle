"""Read the lookup labels (idx:orth / idx:iform values) back out of built XHTML pages."""

import html
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..utils import kindle_fold

ENTRY_PATTERN = re.compile(
    r"<idx:entry\b[^>]*\bid=\"([^\"]*)\"[^>]*>(.*?)</idx:entry>", re.DOTALL
)
ORTH_PATTERN = re.compile(r"<idx:orth\b[^>]*\bvalue=\"([^\"]*)\"")
IFORM_PATTERN = re.compile(r"<idx:iform\b[^>]*\bvalue=\"([^\"]*)\"")
POS_PATTERN = re.compile(r"<p class=\"pos\">(.*?)</p>")


@dataclass
class IndexedEntry:
    key: str  # "<file>#<id>", unique across the dictionary
    headword: str
    pos: str | None
    is_inflection_card: bool
    labels: list[str] = field(default_factory=list)


@dataclass
class LabelIndex:
    """Every label in stored order, grouped by the weights a Kindle searches by."""

    entries: list[IndexedEntry]
    by_fold: dict[str, list[tuple[str, IndexedEntry]]]

    def run(self, word):
        """Labels a tapped word reaches: same weights, in stored order."""
        return self.by_fold.get(kindle_fold(word), [])


def read_entries(pages_dir):
    """Parse entries from the dictionary's XHTML pages, in spine order."""
    pages = sorted(Path(pages_dir).glob("*.xhtml"), key=_spine_order)
    entries = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for entry_id, body in ENTRY_PATTERN.findall(text):
            orth = ORTH_PATTERN.search(body)
            headword = html.unescape(orth.group(1)) if orth else ""
            pos = POS_PATTERN.search(body)
            labels = [headword] if orth else []
            labels += [html.unescape(v) for v in IFORM_PATTERN.findall(body)]
            entries.append(
                IndexedEntry(
                    key=f"{page.name}#{entry_id}",
                    headword=headword,
                    pos=html.unescape(pos.group(1)) if pos else None,
                    is_inflection_card=entry_id.startswith("inf_"),
                    labels=labels,
                )
            )
    return entries


def build_index(entries):
    by_fold = defaultdict(list)
    for entry in entries:
        for label in dict.fromkeys(entry.labels):
            by_fold[kindle_fold(label)].append((label, entry))
    return LabelIndex(entries, dict(by_fold))


def _spine_order(page):
    # make_opf lists main pages, then inf- pages, then ex- pages
    name = page.name
    prefix = 1 if name.startswith("inf-") else 2 if name.startswith("ex-") else 0
    return prefix, name
