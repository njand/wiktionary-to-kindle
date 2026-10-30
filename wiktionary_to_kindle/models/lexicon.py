"""Lexicon model stage: read the merged dump as Entry objects."""

from tqdm import tqdm

from ..jsonl import json_loads
from .entry import Entry


def count_lines(path):
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def read_entries(path, language, limit=None, desc=None, total=None):
    """Yield the dump's entries that render, numbered 1, 2, ... in file order, stopping
    after limit of them. total is the line count shown by the progress bar."""
    entry_id = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in tqdm(f, unit="lines", unit_scale=True, total=total, desc=desc):
            json_entry = json_loads(line)
            entry = Entry(json_entry, language, entry_id + 1)
            if not entry.valid_pairs():
                continue
            entry_id += 1
            yield entry
            if limit is not None and entry_id >= limit:
                break
