"""List the entries a tap reaches with the one a reader most likely means first.

A tap lists every entry it reaches: the one spelled exactly like the tapped word first,
then the rest in the order kindling stores their labels (device test, 2026-10-29: `non`
listed nōnae, by its `Non.`, before nōn). kindling (0.45.6, `mobi.rs`) orders labels with
the same weights by a chain of rules: labels the Kindle rewrites when tapped (`se-`,
`Non.`) and labels with apostrophes first, then fewer accented letters, fewer capitals,
fewer units that weigh nothing (a soft hyphen), and so on.

With no frequency data, how often an entry is meant is estimated from how much Wiktionary
says about it (its JSON without the inflection table, which would make any verb dwarf a
particle), doubled where the spelling is its headword, and a tenth for a proper name or
an alternative spelling (sī's Old Latin se).

For every spelling without accents that reaches several entries (`se`), the entries are
ranked by that estimate and each gets the spelling as a label with as many soft hyphens
as its rank (suī `se`, sē `s­e`, seipse `s­­e`, ...). Those labels have no accents or
capitals, so they come before every other label of the spelling and in rank order: a tap
without macrons lists the entries in that order, and a macronized tap lists the entry
spelled like it first, then the rest in that order. An entry's other labels of the
spelling that would come before them (punctuated, like `se-` and `Non.`) or that are the
plain spelling itself are dropped; the ranked label reaches the same taps. Its labels with
macrons or capitals stay, so a tap spelled exactly like one still opens it first.
"""

import html
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..jsonl import json_dumps
from ..utils import kindle_fold
from .shared_labels import ENTRY_PATTERN, mark

VALUE_PATTERN = re.compile(r'<idx:(?:orth|iform)\b[^>]*?\bvalue="([^"]*)"')
ORTH_PATTERN = re.compile(r'(<idx:orth\b[^>]*?\bvalue=")([^"]*)(")')
IFORM_PATTERN = re.compile(r'<idx:iform\b[^>]*?\bvalue="([^"]*)"')
INFL_PATTERN = re.compile(r"<idx:infl>.*?</idx:infl>", re.DOTALL)
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
    lookup_spellings = entry.language.lookup_spellings
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
        if entry.language.alternative_tags & set(form.get("tags", [])):
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


def rank_spellings(pages, weights):
    """Give every entry a spelling without accents reaches a label of that spelling with
    its rank in soft hyphens, and drop the labels that would come before it (see the
    module docstring). Return the number of entries changed."""
    pages = list(pages)
    reached = defaultdict(list)  # fold -> [(score, entry id)]
    for entry_id, labels in entry_labels(pages):
        for fold, score in weights[entry_id].by_fold(labels).items():
            reached[fold].append((score, entry_id))

    ranked = defaultdict(dict)  # entry id -> {fold: its label}
    for fold, entries in reached.items():
        if len(entries) > 1 and fold.isascii() and fold.isalpha():
            entries.sort(key=lambda e: -e[0])  # stable: page order on a tie
            for rank, (_score, entry_id) in enumerate(entries):
                ranked[entry_id][fold] = mark(fold, rank) if rank else fold
    del reached

    changed = 0

    def rewrite(match):
        nonlocal changed
        own = ranked.get(int(match.group(2)))
        if not own:
            return match.group(0)
        body = match.group(4)
        orth = ORTH_PATTERN.search(body)
        headword = html.unescape(orth.group(2))
        if _queues_ahead(headword, own):
            headword = own[kindle_fold(headword)]
        iforms = [
            form
            for form in map(html.unescape, IFORM_PATTERN.findall(body))
            if not _queues_ahead(form, own)
        ]
        iforms += own.values()
        iforms = [f for f in dict.fromkeys(iforms) if f != headword]
        infl = "".join(
            f'<idx:iform value="{html.escape(f)}" exact="yes" />' for f in iforms
        )
        body = INFL_PATTERN.sub("", body, count=1)
        body = (
            body[: orth.start(2)]
            + html.escape(headword)
            + body[orth.end(2) : body.index("</idx:orth>")]
            + (f"<idx:infl>{infl}</idx:infl>" if infl else "")
            + body[body.index("</idx:orth>") :]
        )
        changed += 1
        return match.group(1) + match.group(2) + match.group(3) + body + match.group(5)

    for page in pages:
        text = Path(page).read_text("utf-8")
        new = ENTRY_PATTERN.sub(rewrite, text)
        if new != text:
            Path(page).write_text(new, encoding="utf-8")
    return changed


def _queues_ahead(label, ranked):
    """Whether label, one of an entry's, would come before or collide with the ranked
    labels in kindling's order: it folds to a ranked spelling and is that spelling
    itself, or has a unit that weighs nothing (punctuation)."""
    fold = kindle_fold(label)
    if fold not in ranked or label == ranked[fold]:
        return False
    return label == fold or any(not kindle_fold(char) for char in label)
