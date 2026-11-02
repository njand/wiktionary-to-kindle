"""Read the lookup labels (idx:orth / idx:iform values) back out of built XHTML pages."""

import html
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..render.headline import POS_NAMES
from ..render.shared_labels import unmark
from ..utils import kindle_fold

ENTRY_PATTERN = re.compile(
    r"<idx:entry\b[^>]*\bid=\"([^\"]*)\"[^>]*>(.*?)</idx:entry>", re.DOTALL
)
ORTH_PATTERN = re.compile(r"<idx:orth\b[^>]*\bvalue=\"([^\"]*)\"")
IFORM_PATTERN = re.compile(r"<idx:iform\b[^>]*\bvalue=\"([^\"]*)\"")
# The part of speech closing the headword line (" · <i>noun</i></p>"); older builds gave
# it a paragraph of its own (<p><i>noun</i></p>, and earlier <p class="pos">)
POS_PATTERN = re.compile(
    r"&#183; <i>([^<,]*)|<p(?: class=\"pos\">|><i>)([^<]*)(?:</i>)?</p>"
)
POS_CODES = {name: code for code, name in POS_NAMES.items()}


@dataclass
class IndexedEntry:
    key: str  # "<file>#<id>", unique across the dictionary
    headword: str  # without the soft hyphens that keep a shared label distinct
    pos: str | None
    is_card: bool  # a disambiguation card (older builds), not an entry
    labels: list[str] = field(default_factory=list)  # as stored, soft hyphens included


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
            label = html.unescape(orth.group(1)) if orth else ""
            pos = POS_PATTERN.search(body)
            labels = [label] if orth else []
            labels += [html.unescape(v) for v in IFORM_PATTERN.findall(body)]
            entries.append(
                IndexedEntry(
                    key=f"{page.name}#{entry_id}",
                    headword=unmark(label),
                    pos=_pos_code(pos),
                    is_card=entry_id.startswith("card_"),
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
    # Older builds listed main pages, then card- pages
    return page.name.startswith("card-"), page.name


def _pos_code(match):
    """Kaikki's code for the part of speech an entry shows ("adjective" → "adj")."""
    if not match:
        return None
    shown = html.unescape(match.group(1) or match.group(2))
    return POS_CODES.get(shown, shown)
