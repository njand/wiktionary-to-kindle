"""python -m wiktionary_to_kindle.quality {stats,diff,coverage,sample} ...

stats DICT_DIR -o stats.json        index statistics of a built dictionary
diff OLD.json NEW.json              markdown comparison of two builds' statistics
coverage DICT_DIR MANIFEST -o OUT   lookup coverage of a corpus (OUT.json, OUT.md)
coverage-diff OLD.json NEW.json     markdown comparison of two builds' coverage
notes DIR [--previous DIR]          a release's notes from its stats and coverage files
sample DUMP.jsonl OUT.jsonl         small, self-consistent sample of a filtered dump
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from ..languages import LANGUAGES, get_language
from . import coverage, stats
from .corpus import load_source, read_manifest, tokenize
from .labels import build_index, read_entries
from .notes import release_notes
from .sample import extract_sample


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m wiktionary_to_kindle.quality")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("stats", help="index statistics of a built dictionary")
    p.add_argument("dict_dir", type=Path, help="e.g. outputs/KindleDictionary-la")
    p.add_argument("-o", "--output", type=Path)

    p = sub.add_parser("diff", help="compare two stats.json files")
    p.add_argument("old", type=Path)
    p.add_argument("new", type=Path)
    p.add_argument("--threshold", type=float, default=0.02)
    p.add_argument(
        "--fail-on-drop",
        action="store_true",
        help="exit 1 if entries, labels or folded keys drop by more than the threshold",
    )

    p = sub.add_parser("coverage", help="lookup coverage of a corpus")
    p.add_argument("dict_dir", type=Path)
    p.add_argument("manifest", type=Path, help="e.g. corpus/la.tsv")
    p.add_argument("-o", "--output", type=Path, help="writes OUTPUT.json and OUTPUT.md")
    p.add_argument("--cache", type=Path, default=Path("corpus/cache"))
    p.add_argument("--lang", default="la", choices=sorted(LANGUAGES))
    p.add_argument(
        "--kindling", help="also check the most frequent words with kindling"
    )
    p.add_argument("--mobi", type=Path, help="built .mobi for --kindling")
    p.add_argument(
        "--verify", type=int, default=300, help="words to check with kindling"
    )

    p = sub.add_parser("coverage-diff", help="compare two coverage .json reports")
    p.add_argument("old", type=Path)
    p.add_argument("new", type=Path)
    p.add_argument(
        "--threshold",
        type=float,
        default=0.005,
        help="largest allowed change in a token share (default: %(default)s = 0.5 pp)",
    )
    p.add_argument(
        "--fail-on-drop",
        action="store_true",
        help="exit 1 if any source's coverage drops by more than the threshold",
    )

    p = sub.add_parser("notes", help="a release's notes")
    p.add_argument(
        "current", type=Path, help="folder with stats-LANG.json and the rest"
    )
    p.add_argument(
        "--previous", type=Path, help="the same files from the latest release"
    )
    p.add_argument("--intro", type=Path, help="markdown to put before the table")

    p = sub.add_parser("sample", help="cut a small sample from a filtered dump")
    p.add_argument("src", type=Path)
    p.add_argument("dst", type=Path)
    p.add_argument("--lemmas", type=int, default=2000)
    p.add_argument(
        "--include",
        type=Path,
        default=Path("tests/lookup_words_la.txt"),
        help="word list whose words (and their lemmas) are always included",
    )
    p.add_argument("--lang", default="la", choices=sorted(LANGUAGES))

    args = parser.parse_args(argv)
    return COMMANDS[args.command](args)


def run_stats(args):
    result = stats.collect(args.dict_dir)
    if args.output:
        stats.write(result, args.output)
    print(
        json.dumps({k: v for k, v in result.items() if k != "largest_ties"}, indent=1)
    )
    return 0


def run_diff(args):
    markdown, regressions = stats.diff(
        stats.load(args.old), stats.load(args.new), args.threshold
    )
    print(markdown)
    for regression in regressions:
        print(f"\n**Possible regression:** {regression}")
    return 1 if regressions and args.fail_on_drop else 0


def run_coverage(args):
    language = get_language(args.lang)
    index = build_index(read_entries(args.dict_dir / "files"))
    report = {"sources": {}}
    overall = Counter()
    for name, fmt, url in read_manifest(args.manifest):
        counts = tokenize(load_source(name, fmt, url, args.cache))
        overall.update(counts)
        report["sources"][name] = coverage.measure(index, counts, language)
    report["overall"] = coverage.measure(index, overall, language)
    report["sources"]["all"] = report["overall"]
    if args.kindling:
        report["kindling"] = coverage.verify_with_kindling(
            index, overall, args.kindling, args.mobi, args.verify
        )

    markdown = coverage.to_markdown(report)
    if args.output:
        args.output.with_suffix(".json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        args.output.with_suffix(".md").write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


def run_coverage_diff(args):
    markdown, regressions = coverage.diff(
        stats.load(args.old), stats.load(args.new), args.threshold
    )
    print(markdown)
    for regression in regressions:
        print(f"\n**Coverage regression:** {regression}")
    return 1 if regressions and args.fail_on_drop else 0


def run_notes(args):
    intro = args.intro.read_text(encoding="utf-8") if args.intro else ""
    sys.stdout.write(release_notes(args.current, args.previous, intro=intro))
    return 0


def run_sample(args):
    include = []
    if args.include and args.include.exists():
        for line in args.include.read_text(encoding="utf-8").splitlines():
            word = line.split("#", 1)[0].strip().removeprefix("xfail:").strip()
            if word:
                include.append(word)
    count = extract_sample(
        args.src, args.dst, get_language(args.lang), args.lemmas, include
    )
    print(f"Wrote {count} entries to {args.dst}")
    return 0


COMMANDS = {
    "stats": run_stats,
    "diff": run_diff,
    "coverage": run_coverage,
    "coverage-diff": run_coverage_diff,
    "notes": run_notes,
    "sample": run_sample,
}

if __name__ == "__main__":
    sys.exit(main())
