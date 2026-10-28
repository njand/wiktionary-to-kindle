import datetime
import gzip
import json
import shutil
import subprocess
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path

from tqdm import tqdm

KAIKKI_RAW_DUMP_URL = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def download_kaikki_dump(lang: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filtered_output_path = output_dir / f"kaikki-{lang}.jsonl"
    gz_dump_path = output_dir / "raw-wiktextract-data.jsonl.gz"

    if filtered_output_path.exists():
        return filtered_output_path

    if not gz_dump_path.exists():
        download(KAIKKI_RAW_DUMP_URL, gz_dump_path)

    print(f"Filtering entries for '{lang}'...")
    filter_dump(gz_dump_path, lang, filtered_output_path)
    return filtered_output_path


def partial_path(path: Path) -> Path:
    """Where path is written until it is complete, so an interrupted run never leaves a
    truncated file that a later run would mistake for a finished one."""
    return path.with_name(path.name + ".part")


def date_path(path: Path) -> Path:
    """Where the date of the Wiktionary data in path is kept."""
    return path.with_name(path.name + ".date")


def dump_date(path) -> str:
    """The date (YYYY-MM-DD) of the Wiktionary data in path or the dump it was filtered or
    sorted from, as Kaikki's server gave it; else the date the file was last written."""
    path = Path(path)
    unsorted = path.with_name(path.name.replace("(sorted)", ""))
    for candidate in (path, unsorted):
        if date_path(candidate).exists():
            return date_path(candidate).read_text(encoding="utf-8").strip()
    mtime = path.stat().st_mtime
    return datetime.date.fromtimestamp(mtime).isoformat()


def download(url: str, path: Path):
    part = partial_path(path)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as response, open(part, "wb") as f:
        total_size = int(response.info().get("Content-Length", 0))
        last_modified = response.info().get("Last-Modified")
        with tqdm(
            total=total_size, unit="B", unit_scale=True, desc="Downloading dump"
        ) as pbar:
            while chunk := response.read(2 * 1024 * 1024):
                f.write(chunk)
                pbar.update(len(chunk))
    part.replace(path)
    if last_modified:
        date = parsedate_to_datetime(last_modified).date().isoformat()
        date_path(path).write_text(date, encoding="utf-8")


def filter_dump(gz_dump_path: Path, lang: str, output_path: Path):
    """Write the lines of the gzipped dump that belong to lang to output_path."""
    part = partial_path(output_path)

    decompressor = next(
        (tool for tool in ("pigz", "zcat", "gzip") if shutil.which(tool)), None
    )
    if decompressor and shutil.which("rg"):
        print(f"Using fast CLI pipeline ({decompressor} + ripgrep)...")
        decomp_cmd = [decompressor, str(gz_dump_path)]
        if decompressor != "zcat":
            decomp_cmd.insert(1, "-dc")
        # A prefilter: it also keeps lines where lang only appears nested (translations,
        # descendants); merge_dump checks the top-level lang_code
        rg_cmd = ["rg", f'"lang_code":\\s*"{lang}"']
        pipe_commands(decomp_cmd, rg_cmd, part)
    else:
        print(
            "Notice: Fast CLI tools (pigz/zcat and ripgrep) not detected. Falling back to standard Python extraction."
        )
        with (
            gzip.open(gz_dump_path, "rt", encoding="utf-8") as gz_in,
            open(part, "w", encoding="utf-8") as jsonl_out,
        ):
            target_token = f'"lang_code": "{lang}"'
            for line in gz_in:
                if target_token in line and json.loads(line).get("lang_code") == lang:
                    jsonl_out.write(line)

    part.replace(output_path)
    if date_path(gz_dump_path).exists():
        shutil.copyfile(date_path(gz_dump_path), date_path(output_path))


def pipe_commands(first_cmd, second_cmd, output_path):
    """Run first_cmd | second_cmd > output_path without a shell."""
    with open(output_path, "wb") as out:
        first = subprocess.Popen(first_cmd, stdout=subprocess.PIPE)
        second = subprocess.run(second_cmd, stdin=first.stdout, stdout=out, check=False)
        first.stdout.close()
        first.wait()
    for cmd, returncode in (
        (first_cmd, first.returncode),
        (second_cmd, second.returncode),
    ):
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd)
