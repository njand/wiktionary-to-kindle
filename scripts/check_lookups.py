"""Check which words a built dictionary opens on a Kindle, using `kindling-cli lookup`.

kindling's simulator predicts what a Paperwhite 5 opens when a word is tapped. For each
word in the list this prints whether it opens, the label it matched, how many labels tied
(the Kindle then picks by stored order), and any labels the index order hides.

Usage:
    python scripts/check_lookups.py outputs/KindleDictionary-la/la-wiktionary.mobi \
        tests/lookup_words_la.txt [--kindling kindling-cli]

Word list: one word per line, `#` comments. Prefix a word with `xfail:` for a known gap;
it is reported but does not fail the run. Exits 1 if any other word opens nothing.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

RESOLVED = re.compile(r'resolves (?:via "(?P<label>.*)"|\(exact headword/alias\))')
RUN = re.compile(r"index search returned (\d+) labels")
HIDDEN = re.compile(r"so the search cannot reach")


def read_words(path):
    words = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        xfail = line.startswith("xfail:")
        words.append((line.removeprefix("xfail:").strip(), xfail))
    return words


def lookup(kindling, mobi, word):
    proc = subprocess.run(
        [kindling, "lookup", str(mobi), word],
        check=False,  # exit 1 means the word opens nothing, which we report
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


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("mobi", type=Path)
    parser.add_argument("words", type=Path)
    parser.add_argument(
        "--kindling",
        default=shutil.which("kindling-cli") or "kindlegen",
        help="kindling binary (CI installs it as `kindlegen`)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    failures = 0
    for word, xfail in read_words(args.words):
        result = lookup(args.kindling, args.mobi, word)
        if result["opens"]:
            status = "XPASS" if xfail else "ok"
        else:
            status = "xfail" if xfail else "MISS"
            failures += not xfail

        notes = []
        if result["label"] and result["label"] != word:
            notes.append(f"via {result['label']}")
        if result["tied"] > 1:
            notes.append(f"{result['tied']} labels tied")
        if result["hidden"]:
            notes.append("index hides a label")
        print(f"{status:6} {word:20} {', '.join(notes)}")
        if args.verbose or status in ("MISS", "XPASS"):
            for line in result["detail"].splitlines():
                print(f"         {line}")

    print(f"\n{failures} unexpected miss(es)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
