"""Put the entry a reader most likely means first in the popup.

A tap lists every entry it reaches: the one spelled exactly like the tapped word first,
then the rest in the order kindling stores their labels (device test, 2026-10-29: `non`
listed nōnae, by its `Non.`, before nōn). A tap in a text without macrons matches no
macronized label exactly, so that order decided which entry came first.

With no frequency data, how often an entry is meant is estimated from how much Wiktionary
says about it (its JSON without the inflection table, which would make any verb dwarf a
particle), doubled where the spelling is its headword, and a tenth for a proper name or
an alternative spelling (sī's Old Latin se). For every spelling several entries share
without accents, the entry with the highest estimate gets that spelling (non, the label
folded the way a Kindle folds a tap) as a label of its own, so it opens first; where
entries share a label exactly, it keeps the plain one (shared_labels).
"""

import html
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..jsonl import json_dumps
from ..merge.forms import ALTERNATIVE_TAGS
from ..utils import kindle_fold, lookup_spellings

ENTRY_PATTERN = re.compile(
    r"(<idx:entry\b[^>]*\bid=\")(\d+)(\"[^>]*>)(.*?)(</idx:entry>)", re.DOTALL
)
VALUE_PATTERN = re.compile(r'<idx:(?:orth|iform)\b[^>]*?\bvalue="([^"]*)"')
HEADWORD, FORM, MINOR = 2.0, 1.0, 0.1


@dataclass(frozen=True)
class Weight:
    """An entry's estimated frequency, and the spellings that change it."""

    size: int
    headwords: frozenset[str]
    alternatives: frozenset[str]  # spellings the entry has only as alternatives

    def score(self, label):
        if label in self.headwords:
            return self.size * HEADWORD
        if label in self.alternatives:
            return self.size * MINOR
        return self.size * FORM

    def by_fold(self, labels):
        """The entry's best score for each folded spelling among labels."""
        scores = {}
        for label in labels:
            fold = kindle_fold(label)
            scores[fold] = max(scores.get(fold, 0), self.score(label))
        return scores


def weigh(entry):
    json_entry = entry.json_entry
    forms = json_entry.get("forms", [])
    size = len(json_dumps(json_entry)) - len(json_dumps(forms))
    if entry.pos == "name":
        size *= MINOR
    headwords = {
        spelling
        for header in entry.headers
        for spelling in lookup_spellings(header.head_word)
    }
    alternative, other = set(), set(headwords)
    for form in forms:
        spellings = lookup_spellings(form.get("form", ""))
        if ALTERNATIVE_TAGS & set(form.get("tags", [])):
            alternative.update(spellings)
        else:
            other.update(spellings)
    return Weight(size, frozenset(headwords), frozenset(alternative - other))


def entry_labels(pages):
    """(entry id, its labels as written) for every entry in pages, in order."""
    for page in pages:
        for match in ENTRY_PATTERN.finditer(Path(page).read_text("utf-8")):
            values = VALUE_PATTERN.findall(match.group(4))
            yield int(match.group(2)), [html.unescape(v) for v in values]


def add_plain_spellings(pages, weights):
    """Give the entry with the highest estimate among those a spelling without accents
    reaches that spelling as a label, where it has none. Return the number added."""
    pages = list(pages)
    best = {}  # fold -> (score, entry id)
    reached = defaultdict(int)
    for entry_id, labels in entry_labels(pages):
        for fold, score in weights[entry_id].by_fold(labels).items():
            reached[fold] += 1
            if fold not in best or score > best[fold][0]:
                best[fold] = (score, entry_id)

    added = defaultdict(list)
    for fold, (_score, entry_id) in best.items():
        if reached[fold] > 1 and fold.isascii() and fold.isalpha():
            added[entry_id].append(fold)
    del best, reached

    count = 0

    def insert(match):
        nonlocal count
        new = [
            f for f in added.get(int(match.group(2)), []) if f not in labels_of(match)
        ]
        if not new:
            return match.group(0)
        count += len(new)
        iforms = "".join(
            f'<idx:iform value="{html.escape(f)}" exact="yes" />' for f in new
        )
        body = match.group(4)
        if "</idx:infl>" in body:
            body = body.replace("</idx:infl>", iforms + "</idx:infl>", 1)
        else:
            body = body.replace(
                "</idx:orth>", f"<idx:infl>{iforms}</idx:infl></idx:orth>", 1
            )
        return match.group(1) + match.group(2) + match.group(3) + body + match.group(5)

    for page in pages:
        text = Path(page).read_text("utf-8")
        new = ENTRY_PATTERN.sub(insert, text)
        if new != text:
            Path(page).write_text(new, encoding="utf-8")
    return count


def labels_of(match):
    return {html.unescape(v) for v in VALUE_PATTERN.findall(match.group(4))}
