"""prepare-book: split the Turkish words of an e-book that the dictionary cannot reach, so a
tap on the stem opens its entry.

    prepare-book book.epub -o book-prepared.epub
    prepare-book book.epub --decide rooted          # no model: the stem of the lemma
    prepare-book book.epub --kindling kindling-cli  # also build book-prepared.azw3

The decisions are cached beside the book (book.splits.jsonl); a report of every split is
written beside the output (book-prepared.splits.tsv). Books with DRM cannot be read.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from . import model
from .epub import prepare_epub, prepare_plain
from .lexicon import Lexicon
from .segment import greedy, rooted

DEFAULT_DICT = Path("outputs/KindleDictionary-tr")


def choose_decider(args):
    """The decider --decide names; auto is the model when credentials or a Claude CLI
    are there, else rooted."""
    name = args.decide
    cache = model.Cache(args.cache)
    if name == "auto":
        has_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN"
        )
        try:
            import anthropic  # noqa: F401

            has_sdk = True
        except ImportError:
            has_sdk = False
        if has_key and has_sdk:
            name = "model"
        elif shutil.which("claude"):
            name, args.backend = "model", "claude-cli"
        else:
            print(
                "No model available (no ANTHROPIC_API_KEY with the anthropic package, "
                "no claude CLI): splitting by the stem of each word's lemma instead "
                "(--decide rooted). Cached model decisions are still used.",
                file=sys.stderr,
            )
            name = "rooted-cached"
    if name == "model":
        return model.ModelDecider(cache, args.backend, args.model, args.effort)
    if name == "rooted-cached":
        return model.CachedDecider(cache, fallback=rooted)
    if name == "export":
        return model.Recorder(cache, fallback=rooted)
    return {"greedy": greedy, "rooted": rooted}[name]


def build_azw3(epub, out, kindling):
    """Build out (.azw3) from the prepared EPUB with kindling."""
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(epub) as z:
            z.extractall(tmp)
        opf = next(Path(tmp).rglob("*.opf"))
        command = [kindling, "build", opf.name, "-o", str(Path(out).resolve())]
        if subprocess.run(command, check=False, cwd=opf.parent).returncode != 0:
            # kindling holds a book to Amazon's store rules (a table of contents, ...),
            # which a book read from documents/ need not meet
            print(
                "kindling's checks failed on the book; building it without them",
                file=sys.stderr,
            )
            subprocess.run([*command, "--no-validate"], cwd=opf.parent, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="prepare-book", description=__doc__.split("\n\n")[0]
    )
    parser.add_argument("book", type=Path, help="an .epub (or a .txt) without DRM")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--lang", default="tr", choices=["tr"])
    parser.add_argument(
        "--dict", type=Path, default=DEFAULT_DICT, help="the built dictionary"
    )
    parser.add_argument(
        "--decide",
        default="auto",
        choices=["auto", "model", "rooted", "greedy", "export"],
        help="who chooses each split (default: a model if one is available)",
    )
    parser.add_argument(
        "--backend", default="anthropic", choices=["anthropic", "claude-cli"]
    )
    parser.add_argument("--model", default=model.DEFAULT_MODEL)
    parser.add_argument("--effort", default="low", help="model effort (%(default)s)")
    parser.add_argument(
        "--cache", type=Path, help="decision cache (default: beside the book)"
    )
    parser.add_argument(
        "--requests",
        type=Path,
        help="with --decide export: where to write the requests",
    )
    parser.add_argument("--no-nowrap", action="store_true", help="let split words wrap")
    parser.add_argument("--kindling", help="kindling binary, to also build an .azw3")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    if not args.book.exists():
        parser.error(f"no such book: {args.book}")
    if not (args.dict / "files").is_dir():
        parser.error(
            f"no built dictionary in {args.dict} (run wiktionary-to-kindle --lang tr)"
        )
    suffix = args.book.suffix.lower()
    args.output = args.output or args.book.with_name(
        f"{args.book.stem}-prepared{suffix}"
    )
    args.cache = args.cache or args.book.with_name(f"{args.book.stem}.splits.jsonl")

    print(f"Reading the dictionary in {args.dict}...")
    lexicon = Lexicon.load(args.dict)
    decide = choose_decider(args)
    if suffix == ".epub":
        report = prepare_epub(
            args.book, args.output, lexicon, decide, not args.no_nowrap
        )
    else:
        text, report = prepare_plain(
            args.book.read_text(encoding="utf-8"), lexicon, decide
        )
        args.output.write_text(text, encoding="utf-8")

    splits = [(w, s, split) for w, s, split in report if split]
    tsv = args.output.with_name(f"{args.output.stem}.splits.tsv")
    with tsv.open("w", encoding="utf-8") as f:
        f.write("word\tsplit\tstem opens\tsentence\n")
        for word, sentence, split in splits:
            opens = "; ".join(s.headword for s in split.senses[:3])
            f.write(f"{word}\t{split.stem}|{split.rest}\t{opens}\t{sentence}\n")
    print(
        f"Wrote {args.output}: {len(splits):,} words split of {len(report):,} that "
        f"needed a decision (report: {tsv})"
    )
    if isinstance(decide, model.ModelDecider):
        print(
            f"Model {decide.model}: {decide.requests:,} requests, "
            f"{decide.usage['input_tokens']:,} input and "
            f"{decide.usage['output_tokens']:,} output tokens"
        )
    if isinstance(decide, model.Recorder):
        requests = args.requests or args.output.with_name(
            f"{args.output.stem}.requests.jsonl"
        )
        model.export_requests(decide, requests)
        print(f"Wrote {len(decide.requests):,} model requests to {requests}")
    if args.kindling and suffix == ".epub":
        azw3 = args.output.with_suffix(".azw3")
        build_azw3(args.output, azw3, args.kindling)
        print(f"Wrote {azw3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
