"""Index statistics for a built dictionary, and a diff between two builds.

A silent loss (like form-of entries dropped by a merge-key mismatch) shows up as a drop in
entries, labels or folded keys between releases, even when every test still passes.
"""

import json
from collections import Counter
from pathlib import Path

from .labels import build_index, read_entries

SCALARS = (
    "entries",
    "inflection_cards",
    "labels",
    "folded_keys",
    "tied_keys",
    "max_labels_per_entry",
    "pages",
    "mobi_bytes",
)
# Shrinking any of these is usually lost data; ties shrinking is progress
WATCHED = ("entries", "labels", "folded_keys")


def collect(dict_dir):
    dict_dir = Path(dict_dir)
    entries = read_entries(dict_dir / "files")
    index = build_index(entries)
    main = [e for e in entries if not e.is_inflection_card]

    ties = []
    for fold, run in index.by_fold.items():
        heads = list(dict.fromkeys(e.headword for _, e in run))
        if len({e.key for _, e in run}) > 1:
            ties.append((fold, len({e.key for _, e in run}), heads))
    ties.sort(key=lambda t: (-t[1], t[0]))

    return {
        "entries": len(main),
        "inflection_cards": len(entries) - len(main),
        "labels": sum(len(set(e.labels)) for e in entries),
        "folded_keys": len(index.by_fold),
        "tied_keys": len(ties),
        "max_labels_per_entry": max((len(set(e.labels)) for e in entries), default=0),
        "pages": len(list((dict_dir / "files").glob("*.xhtml"))),
        "mobi_bytes": sum(p.stat().st_size for p in dict_dir.glob("*.mobi")),
        "pos": dict(Counter(e.pos or "(none)" for e in main).most_common()),
        "largest_ties": [[fold, n, heads[:8]] for fold, n, heads in ties[:25]],
    }


def diff(old, new, threshold=0.02):
    """Return (markdown, regressions) comparing two stats dicts."""
    lines = ["| Metric | Previous | Current | Change |", "| --- | ---: | ---: | ---: |"]
    regressions = []
    for name in SCALARS:
        before, after = old.get(name, 0), new.get(name, 0)
        lines.append(f"| {name} | {before:,} | {after:,} | {_change(before, after)} |")
        if name in WATCHED and before and (before - after) / before > threshold:
            regressions.append(f"{name} dropped {_change(before, after)}")

    pos_rows = []
    for pos in sorted(set(old.get("pos", {})) | set(new.get("pos", {}))):
        before, after = old.get("pos", {}).get(pos, 0), new.get("pos", {}).get(pos, 0)
        if before != after:
            pos_rows.append(
                f"| {pos} | {before:,} | {after:,} | {_change(before, after)} |"
            )
    if pos_rows:
        lines += ["", "| Part of speech | Previous | Current | Change |"]
        lines += ["| --- | ---: | ---: | ---: |", *pos_rows]
    return "\n".join(lines), regressions


def _change(before, after):
    delta = after - before
    if not before:
        return f"{delta:+,}"
    return f"{delta:+,} ({delta / before:+.1%})"


def write(stats, path):
    Path(path).write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
