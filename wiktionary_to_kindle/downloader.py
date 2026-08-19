import gzip
import json
import shutil
import subprocess
import urllib.request
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

    # Step 1: Download full dump
    if not gz_dump_path.exists():
        req = urllib.request.Request(KAIKKI_RAW_DUMP_URL, headers=HEADERS)
        with urllib.request.urlopen(req) as response, open(gz_dump_path, "wb") as f:
            total_size = int(response.info().get("Content-Length", 0))
            with tqdm(
                total=total_size, unit="B", unit_scale=True, desc="Downloading dump"
            ) as pbar:
                while chunk := response.read(2 * 1024 * 1024):
                    f.write(chunk)
                    pbar.update(len(chunk))

    # Step 2: Extract using CLI pipeline if available
    print(f"Filtering entries for '{lang}'...")

    decompressor = (
        "pigz"
        if shutil.which("pigz")
        else (
            "zcat"
            if shutil.which("zcat")
            else ("gzip" if shutil.which("gzip") else None)
        )
    )
    has_rg = shutil.which("rg") is not None

    if decompressor and has_rg:
        print(f"Using fast CLI pipeline ({decompressor} + ripgrep)...")
        decomp_cmd = f"{decompressor} -dc" if decompressor != "zcat" else "zcat"
        pattern = f'"lang_code":\\s*"{lang}"'
        cmd = f"{decomp_cmd} {gz_dump_path} | rg '{pattern}' > {filtered_output_path}"
        subprocess.run(cmd, shell=True, check=True)
        return filtered_output_path

    print(
        "Notice: Fast CLI tools (pigz/zcat and ripgrep) not detected. Falling back to standard Python extraction."
    )

    # Step 3: Pure Python Fallback
    with (
        gzip.open(gz_dump_path, "rt", encoding="utf-8") as gz_in,
        open(filtered_output_path, "w", encoding="utf-8") as jsonl_out,
    ):
        target_token = f'"lang_code": "{lang}"'
        for line in gz_in:
            if target_token in line and json.loads(line).get("lang_code") == lang:
                jsonl_out.write(line)

    return filtered_output_path
