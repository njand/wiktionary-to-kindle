"""Run kindling's on-device lookup simulator (`kindling-cli lookup <mobi> <word>`).

kindling prints one stdout line, `"w" resolves via "label" at text position N` (or
`(exact headword/alias)`), and exits 1 when nothing opens. Notes on stderr say how many
labels tied and whether the index order hides a label from the search.
"""

import re
import subprocess

from ..utils import find_kindling

RESOLVED = re.compile(r'resolves (?:via "(?P<label>.*)"|\(exact headword/alias\))')
RUN = re.compile(r"index search returned (\d+) labels")
HIDDEN = re.compile(r"so the search cannot reach")


def default_binary():
    return str(find_kindling() or "kindling-cli")


def lookup(kindling, mobi, word):
    proc = subprocess.run(
        [kindling, "lookup", str(mobi), word],
        check=False,  # exit 1 means the word opens nothing, which callers report
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    match = RESOLVED.search(proc.stdout)
    run = RUN.search(proc.stderr)
    return {
        "opens": proc.returncode == 0 and match is not None,
        "label": (match.group("label") or word) if match else None,
        "tied": int(run.group(1)) if run else 1,
        "hidden": bool(HIDDEN.search(proc.stderr)),
        "detail": (proc.stdout + proc.stderr).strip(),
    }
