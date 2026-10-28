import argparse
from pathlib import Path

from .ingest import download_kaikki_dump
from .pipeline import build_dictionary
from .utils import find_kindling

DOWNLOADS = Path("downloads")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a Kindle Dictionary from Wiktionary JSONL Dumps."
    )
    parser.add_argument(
        "--lang", default="la", help="Language code (default: %(default)s)"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to existing JSONL file (nothing is downloaded)",
    )
    parser.add_argument(
        "--download",
        dest="auto_download",
        action="store_true",
        default=True,
        help="Download the Kaikki dump unless --input is given (default)",
    )
    parser.add_argument(
        "--no-download",
        dest="auto_download",
        action="store_false",
        help="Use the dump already in downloads/ instead of downloading",
    )
    parser.add_argument(
        "--kindling",
        "--kindlegen",
        dest="kindling",
        type=Path,
        default=None,
        help="Path to the kindling-cli executable (default: searched on PATH)",
    )
    # Sorting always runs, and its output is cached; still accepted by old scripts
    parser.add_argument("--sort", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--resort",
        action="store_true",
        help="Sort the JSONL again even if a cached sorted file is up to date",
    )
    parser.add_argument(
        "--descendants",
        nargs="+",
        default=["English", "Portuguese", "Spanish", "French", "Italian"],
        help="Descendant languages to retain",
    )
    return parser, parser.parse_args(argv)


def choose_input(parser, args):
    """The dump to build from: --input, else a download, else the one in downloads/."""
    if args.input:
        if not args.input.is_file():
            parser.error(f"--input file '{args.input}' does not exist.")
        return args.input
    if args.auto_download:
        return download_kaikki_dump(args.lang, output_dir=DOWNLOADS)

    raw_file = DOWNLOADS / f"kaikki-{args.lang}.jsonl"
    sorted_file = DOWNLOADS / f"kaikki-{args.lang}(sorted).jsonl"
    for candidate in (raw_file, sorted_file):
        if candidate.exists():
            return candidate
    parser.error(
        f"--no-download needs '{raw_file}' (or its sorted file), or a dump given with --input."
    )


def main(argv=None):
    parser, args = parse_args(argv)

    kindling = args.kindling or find_kindling()
    if not kindling:
        parser.error("kindling-cli not found on PATH. Give its path with --kindling.")
    # kindling runs from the output folder, where a relative path breaks; a bare name
    # (kindling-cli) is left for the PATH search
    if Path(kindling).is_file():
        kindling = Path(kindling).resolve()
    elif args.kindling and len(Path(kindling).parts) > 1:
        parser.error(f"--kindling '{args.kindling}' does not exist.")

    input_file = choose_input(parser, args)

    print(f"Building dictionary for language: {args.lang}")
    build_dictionary(
        str(input_file),
        args.lang,
        str(kindling),
        descendant_langs=args.descendants,
        resort=args.resort,
    )


if __name__ == "__main__":
    main()
