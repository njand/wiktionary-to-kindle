import requests
import os
import gzip
import json
from tqdm import tqdm

from KindleDict import KindleDict


def download_file(url, dest_path):
    """Download the most recent dump of Wiktionary."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    with open(dest_path, 'wb') as f:
        for chunk in tqdm(response.iter_content(chunk_size=8192),
                          total=total_size//8192 + 1, unit='KB',
                          desc="Downloading Wiktionary dump"):
            f.write(chunk)

def filter_jsonl_gz_by_lang_code(src_gz_path: str, lang_code: str):
    dest_path = f"../data/filtered_{lang_code}.jsonl"
    total_uncompressed = 20 * 1024 ** 3

    with gzip.open(src_gz_path, 'rt', encoding='utf-8') as f_in, \
         open(dest_path, 'w', encoding='utf-8') as f_out, \
         tqdm(total=total_uncompressed, unit='B', unit_scale=True, desc="Filtering") as pbar:

        for line in f_in:
            pbar.update(len(line.encode('utf-8')))
            obj = json.loads(line)
            if obj.get('lang_code') == lang_code:
                f_out.write(line)
        
        pbar.total = pbar.n
        pbar.refresh()
    
    return dest_path

def download_wiktionary_languages(lang_codes: list[str]):
    """Download Wiktionary dump and filter to selected language(s)"""
    src_gz_path = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
    gz_path = "../data/raw-wiktextract-data.jsonl.gz"

    download_file(src_gz_path, gz_path)
    file_paths = []
    for lang_code in lang_codes:
        fp = filter_jsonl_gz_by_lang_code(gz_path, lang_code)
        file_paths.append(fp)
    
    os.remove(gz_path)
    
    return file_paths

def find_kindlegen():
    possible_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Amazon\Kindle Previewer 3\lib\fc\bin\kindlegen.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Amazon\Kindle Previewer 3\lib\fc\bin\kindlegen.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Amazon\Kindle Previewer 3\lib\fc\bin\kindlegen.exe"),
    ]
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError("kindlegen.exe not found in common locations. Please verify its location and pass it in manually.")


if __name__ == "__main__":
    kindle_gen_path = find_kindlegen()

    lang_codes = ["la"]
    # file_paths = download_wiktionary_languages(lang_codes)
#     file_paths = ['../data/filtered_la(sorted)-short.jsonl']
    file_paths = ['../data/filtered_la(sorted).jsonl']
#     file_paths = ['../data/filtered_la.jsonl']

    for lang_code, input_fp in zip(lang_codes, file_paths):
        kd = KindleDict(input_fp, lang_code, kindle_gen_path)
#         kd.sort_jsonl()
        kd.build_dictionary(max_page_len=5000,
                            limit=None,
                            descendant_langs=["English", "Portuguese", "Spanish", "French", "Italian"],
                            link_examples=False,
                            recursive_senses=True,
                            include_etymology=True,
                            disambiguate_inflections=True)
