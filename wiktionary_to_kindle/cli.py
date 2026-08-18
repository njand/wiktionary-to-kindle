import argparse
from pathlib import Path
from .builders.kindle_dict import KindleDict
from .downloader import download_kaikki_dump
from .utils import find_kindlegen

def main():
    parser = argparse.ArgumentParser(description="Build a Kindle Dictionary from Wiktionary JSONL Dumps.")
    parser.add_argument("--lang", required=True, help="Language code or name (e.g., 'Latin')")
    parser.add_argument("--input", type=Path, default=None, help="Path to existing JSONL file")
    parser.add_argument("--download", dest="auto_download", action="store_true", default=True, help="Automatically download Kaikki dump")
    parser.add_argument("--no-download", dest="auto_download", action="store_false", help="Use local file provided in --input")
    parser.add_argument("--kindlegen", type=Path, help="Path to kindlegen executable", default=None)
    parser.add_argument("--sort", action="store_true", help="Run external merge sort on JSONL before dictionary generation")
    parser.add_argument("--descendants", nargs="+", default=["English", "Portuguese", "Spanish", "French", "Italian"], help="Descendant languages to retain")
    
    args = parser.parse_args()

    kindlegen_path = args.kindlegen or find_kindlegen()
    if not kindlegen_path:
        raise FileNotFoundError("kindlegen executable not found. Provide path via --kindlegen.")

    should_sort = args.sort

    if args.auto_download:
        input_file = download_kaikki_dump(args.lang, output_dir=Path("downloads"))
    elif args.input:
        input_file = args.input
    else:
        downloads_dir = Path("downloads")
        sorted_file = downloads_dir / f"kaikki-{args.lang}(sorted).jsonl"
        raw_file = downloads_dir / f"kaikki-{args.lang}.jsonl"

        if should_sort and sorted_file.exists():
            input_file = sorted_file
            should_sort = False  # Already sorted on disk; skip re-sorting
        elif raw_file.exists():
            input_file = raw_file
        else:
            expected_file = sorted_file if args.sort else raw_file
            parser.error(
                f"--input is required when --no-download is specified and '{expected_file}' does not exist."
            )

    kd = KindleDict(str(input_file), args.lang, str(kindlegen_path))

    if should_sort:
        print("Sorting JSONL file...")
        kd.sort_jsonl()
        
    print(f"Building dictionary for language: {args.lang}")
    kd.build_dictionary(
        descendant_langs=args.descendants,
        link_examples=False,
        recursive_senses=True,
        include_etymology=True
    )

if __name__ == "__main__":
    main()