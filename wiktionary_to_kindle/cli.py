import argparse
from pathlib import Path

from .builders.kindle_dict import KindleDict
from .downloader import download_kaikki_dump
from .utils import find_kindlegen


def main():
    parser = argparse.ArgumentParser(
        description="Build a Kindle Dictionary from Wiktionary JSONL Dumps."
    )
    parser.add_argument("--lang", required=True, default="la", help="Language code")
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
        "--kindlegen", type=Path, help="Path to kindlegen executable", default=None
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="Deprecated: sorting always runs, and its output is cached",
    )
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

    args = parser.parse_args()

    kindlegen_path = args.kindlegen or find_kindlegen()
    if not kindlegen_path:
        raise FileNotFoundError(
            "kindlegen executable not found. Provide path via --kindlegen."
        )

    if args.input:
        if not args.input.is_file():
            parser.error(f"--input file '{args.input}' does not exist.")
        input_file = args.input
    elif args.auto_download:
        input_file = download_kaikki_dump(args.lang, output_dir=Path("downloads"))
    else:
        downloads_dir = Path("downloads")
        sorted_file = downloads_dir / f"kaikki-{args.lang}(sorted).jsonl"
        raw_file = downloads_dir / f"kaikki-{args.lang}.jsonl"

        if raw_file.exists():
            input_file = raw_file
        elif sorted_file.exists():
            input_file = sorted_file
        else:
            parser.error(
                f"--input is required when --no-download is specified and '{raw_file}' does not exist."
            )

    kd = KindleDict(str(input_file), args.lang, str(kindlegen_path))

    # A sorted file is already merged; otherwise sort, reusing an up-to-date cached result
    if not Path(input_file).stem.endswith("(sorted)"):
        kd.sort_jsonl(force=args.resort)

    print(f"Building dictionary for language: {args.lang}")
    kd.build_dictionary(
        descendant_langs=args.descendants,
        link_examples=False,
        recursive_senses=True,
        include_etymology=True,
    )


if __name__ == "__main__":
    main()
