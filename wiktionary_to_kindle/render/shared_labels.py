"""Keep a label for every entry that has it, when entries share a spelling.

kindling stores one index record per label string, so of two entries indexed by the same
spelling (et the conjunction and et the adverb) only one is reached, and the popup lists
only that one (device test, 2026-10-28). A soft hyphen weighs nothing on a Kindle, so a
label with one still reaches its entry from the same taps, but kindling stores it
separately. The first entry with a spelling keeps it as it is; the next gets one soft
hyphen after its first letter, the one after that two, and so on. Entries whose
headword it is come before entries that have it as an inflected form, so a tap spelled
exactly like it opens the headword (a quod rather than quī).

The soft hyphen goes inside the word because one at either end is dropped from a tapped
word: kindling stores such a label ahead of the plain one, and a tap that matches neither
exactly would open it first. A label of one letter has no inside, so it gets them after.
"""

import html
import re
import unicodedata
from collections import Counter
from pathlib import Path

MARKER = "\u00ad"  # soft hyphen

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


def distinguish_shared_labels(pages):
    """Rewrite the idx:orth and idx:iform values in pages (XHTML files, in spine order)
    so that no two entries share one. Return the number of labels changed."""
    pages = list(pages)
    headwords, owners = Counter(), Counter()
    for page in pages:
        for _, kind, value, _ in LABEL_PATTERN.findall(page.read_text("utf-8")):
            owners[value] += 1
            if kind == "orth":
                headwords[value] += 1
    shared = {value for value, count in owners.items() if count > 1}
    del owners

    seen_headwords, seen_forms = Counter(), Counter()
    changed = 0

    def replace(match):
        nonlocal changed
        start, kind, value, end = match.groups()
        if value not in shared:
            return match.group(0)
        if kind == "orth":
            rank = seen_headwords[value]
            seen_headwords[value] += 1
        else:
            rank = headwords[value] + seen_forms[value]
            seen_forms[value] += 1
        if not rank:
            return match.group(0)
        changed += 1
        label = mark(html.unescape(value), rank)
        return start + html.escape(label) + end

    for page in pages:
        text = page.read_text("utf-8")
        new = LABEL_PATTERN.sub(replace, text)
        if new != text:
            Path(page).write_text(new, encoding="utf-8")
    return changed
