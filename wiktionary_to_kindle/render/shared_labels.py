"""Keep a label for every entry that has it, when entries share a spelling.

kindling stores one index record per label string, so of two entries indexed by the same
spelling (et the conjunction and et the adverb) only one is reached, and the popup lists
only that one (device test, 2026-10-28). A soft hyphen weighs nothing on a Kindle, so a
label with one still reaches its entry from the same taps, but kindling stores it
separately. The first entry with a spelling keeps it as it is; the next gets one soft
hyphen after its first letter, the one after that two, and so on. Entries come in the
order of their estimated frequency (popup_order), so a tap spelled exactly like the label
opens the likeliest; on a tie, entries whose headword it is come before entries that have
it as an inflected form (a quod rather than quī), then page order.

The soft hyphen goes inside the word because one at either end is dropped from a tapped
word: kindling stores such a label ahead of the plain one, and a tap that matches neither
exactly would open it first. A label of one letter has no inside, so it gets them after.
"""

import html
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from ..utils import kindle_fold

MARKER = "\u00ad"  # soft hyphen

ENTRY_PATTERN = re.compile(
    r"(<idx:entry\b[^>]*\bid=\")(\d+)(\"[^>]*>)(.*?)(</idx:entry>)", re.DOTALL
)
LABEL_PATTERN = re.compile(r'(<idx:(orth|iform)\b[^>]*?\bvalue=")([^"]*)(")')


def unmark(label):
    """label as Wiktionary spells it."""
    return label.replace(MARKER, "")


def mark(label, count):
    """label with count soft hyphens after its first letter and that letter's marks."""
    end = 1
    while end < len(label) and unicodedata.combining(label[end]):
        end += 1
    return label[:end] + MARKER * count + label[end:]


def distinguish_shared_labels(pages, weights=None):
    """Rewrite the idx:orth and idx:iform values in pages (XHTML files, in spine order)
    so that no two entries share one; weights maps entry ids to popup_order.Weight.
    Return the number of labels changed."""
    pages = list(pages)
    owners = defaultdict(list)  # label -> [(sort key, entry id)]
    for page in pages:
        for match in ENTRY_PATTERN.finditer(page.read_text("utf-8")):
            entry_id = int(match.group(2))
            labels = LABEL_PATTERN.findall(match.group(4))
            scores = (
                weights[entry_id].by_fold(html.unescape(v) for _, _, v, _ in labels)
                if weights
                else {}
            )
            for _, kind, value, _ in labels:
                score = scores.get(kindle_fold(html.unescape(value)), 0)
                key = (-score, kind != "orth", len(owners[value]))
                owners[value].append((key, entry_id))
    ranks = {
        value: [entry_id for _, entry_id in sorted(entries)]
        for value, entries in owners.items()
        if len(entries) > 1
    }
    del owners

    changed = 0

    def replace_in_entry(match):
        entry_id = int(match.group(2))

        def replace(label):
            nonlocal changed
            start, _kind, value, end = label.groups()
            rank = ranks[value].index(entry_id) if value in ranks else 0
            if not rank:
                return label.group(0)
            changed += 1
            return start + html.escape(mark(html.unescape(value), rank)) + end

        body = LABEL_PATTERN.sub(replace, match.group(4))
        return match.group(1) + match.group(2) + match.group(3) + body + match.group(5)

    for page in pages:
        text = page.read_text("utf-8")
        new = ENTRY_PATTERN.sub(replace_in_entry, text)
        if new != text:
            Path(page).write_text(new, encoding="utf-8")
    return changed
