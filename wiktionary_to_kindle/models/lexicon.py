"""Lexicon model stage: read the merged dump as Entry objects."""

from tqdm import tqdm

from ..jsonl import json_dumps, json_loads
from .entry import Entry


def count_lines(path):
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def read_entries(path, limit=None, desc=None, total=None):
    """Yield (entry, size) for the dump's entries that render, numbered 1, 2, ... in
    file order, stopping after limit of them. size is the JSON length without the
    inflection table, a rough measure of how much Wiktionary says about the word (a verb's
    table would dwarf it). total is the line count shown by the progress bar."""
    entry_id = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in tqdm(f, unit="lines", unit_scale=True, total=total, desc=desc):
            json_entry = json_loads(line)
            entry = Entry(json_entry, entry_id + 1)
            if not entry.valid_pairs():
                continue
            entry_id += 1
            yield entry, len(line) - len(json_dumps(json_entry.get("forms", [])))
            if limit is not None and entry_id >= limit:
                break
