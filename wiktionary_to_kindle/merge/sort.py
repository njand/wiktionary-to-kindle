"""Sort the filtered dump by headword and merge each pointer page into its lemma.

The output (`<dump>(sorted).jsonl`) has one line per lemma, with the forms of its pointer
pages (merge.pointers), generated forms (merge.forms) and the merged pages that are words of
their own (merge.related) added to it. It is cached beside the input.
"""

import heapq
import json
import os
import tempfile
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from ..jsonl import USING_ORJSON, json_dumps, json_loads
from ..utils import normalize, remove_breves
from .forms import enrich_forms
from .pointers import (
    collect_forms,
    get_header,
    promote_orphans,
    rekey_plain_roots,
    root_form,
)
from .related import MERGED_KEY

# Bump when merge_dump's output changes, so cached sorted files are rebuilt
SORT_VERSION = 11

SORTED_SUFFIX = "(sorted)"

EXCLUDED_POS = {
    "suffix",
    "character",
    "prefix",
    "symbol",
    "interfix",
    "infix",
    "circumfix",
    "punct",
}


@dataclass
class Merged:
    path: str
    line_count: int | None  # None when the cached file was reused


def is_sorted(path):
    return Path(path).stem.endswith(SORTED_SUFFIX)


def sorted_path(path):
    base, ext = os.path.splitext(path)
    return f"{base}{SORTED_SUFFIX}{ext}"


def cache_meta(path):
    stat = os.stat(path)
    return {
        "sort_version": SORT_VERSION,
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
    }


def sort_key(header):
    return normalize(header, lowercase=True), normalize(header, lowercase=False)


def merge_dump(path, language, chunk_size=200000, force=False):
    """Sort the JSONL file at path with an external merge sort, to prevent disk I/O
    thrashing, merging pointer pages of language (a Language) into their lemmas on the way.

    The result is cached beside the input; it is reused while the input file and
    SORT_VERSION are unchanged, unless force is set.
    """
    output_path = sorted_path(path)
    meta_path = Path(output_path + ".meta.json")
    meta = cache_meta(path)
    cached = (
        not force
        and os.path.exists(output_path)
        and meta_path.exists()
        and json.loads(meta_path.read_text(encoding="utf-8")) == meta
    )
    if cached:
        print(f"Reusing sorted file {output_path} (pass --resort to rebuild it)")
        return Merged(output_path, None)

    print("Sorting JSONL file...")
    if not USING_ORJSON:
        print(
            "Info: `orjson` not detected. Running with standard `json` (install `wiktionary-to-kindle[fast]` for speedups)."
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        chunk_files = []
        current_chunk = []
        # Keyed by macronized headword: Wiktionary's form_of/alt_of targets keep macrons
        pointers = defaultdict(list)
        lemma_pos = defaultdict(set)
        # Every headword, without breves -> its parts of speech
        known = defaultdict(set)

        def write_chunk(chunk_data, chunk_index):
            chunk_data.sort(key=lambda item: sort_key(item[0]))
            chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}.jsonl")
            with open(chunk_path, "w", encoding="utf-8") as out_c:
                for _, _, line in chunk_data:
                    out_c.write(line)
            return chunk_path

        with open(path, "r", encoding="utf-8") as f:
            file_size = f.seek(0, 2)
            f.seek(0)
            with tqdm(
                total=file_size, unit="B", unit_scale=True, desc="Chunking JSONL"
            ) as pbar:
                line_count, chunk_index = 0, 0
                while True:
                    pos = f.tell()
                    line = f.readline()
                    if not line:
                        if current_chunk:
                            chunk_files.append(write_chunk(current_chunk, chunk_index))
                        break

                    pbar.update(f.tell() - pos)
                    obj = json_loads(line)

                    if obj.get("lang_code") != language.code:
                        continue

                    word = normalize(obj["word"], lowercase=False)
                    part_of_speech = obj.get("pos")

                    if (
                        part_of_speech not in EXCLUDED_POS
                        and not word.startswith("-")
                        and not word.endswith("-")
                    ):
                        header = get_header(obj, language)
                        root = root_form(obj.get("senses", []), language)
                        known[remove_breves(header)].add(part_of_speech)

                        if root is None:
                            lemma_pos[remove_breves(header)].add(part_of_speech)
                            current_chunk.append((header, part_of_speech, line))
                            line_count += 1
                            if len(current_chunk) >= chunk_size:
                                chunk_files.append(
                                    write_chunk(current_chunk, chunk_index)
                                )
                                current_chunk = []
                                chunk_index += 1
                        else:
                            pointers[remove_breves(root)].append(
                                (part_of_speech, header, obj)
                            )

        rekey_plain_roots(pointers, known, language.letters)
        orphans = promote_orphans(pointers, lemma_pos)
        promoted = {id(obj) for _, _, obj in orphans}
        if orphans:
            chunk_files.append(
                write_chunk(
                    [(h, p, json_dumps(o) + "\n") for h, p, o in orphans],
                    chunk_index + 1,
                )
            )
            line_count += len(orphans)

        def read_lines(file_obj):
            for fl in file_obj:
                obj = json_loads(fl)
                header = get_header(obj, language)
                # Compute exact sort keys once per line to match write_chunk logic
                yield (*sort_key(header), header, obj.get("pos"), obj)

        # Written under a name of its own and renamed when complete, so neither an
        # interrupted sort nor two sorts at once leave a damaged file behind
        part_path = f"{output_path}.{os.getpid()}.part"
        with ExitStack() as stack:
            out_f = stack.enter_context(open(part_path, "w", encoding="utf-8"))
            files = [
                stack.enter_context(open(cf, "r", encoding="utf-8"))
                for cf in chunk_files
            ]

            merged_iter = heapq.merge(
                *(read_lines(f) for f in files),
                key=lambda x: (x[0], x[1]),
            )

            with tqdm(
                total=line_count,
                unit="lines",
                unit_scale=True,
                desc="Merging Chunks",
            ) as pbar:
                for _lower_word, _raw_word, header, pos, obj in merged_iter:
                    addl_forms, merged = collect_forms(
                        pointers,
                        remove_breves(header),
                        pos,
                        lemma_pos,
                        promoted,
                        language,
                    )
                    forms = enrich_forms(
                        obj.get("forms", []), known, language, addl_forms, obj
                    )
                    if "forms" in obj or forms:
                        obj["forms"] = forms
                    if merged:
                        obj[MERGED_KEY] = merged

                    out_f.write(json_dumps(obj) + "\n")
                    pbar.update(1)

    os.replace(part_path, output_path)
    # Written last, so an interrupted sort is never mistaken for a finished one
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return Merged(output_path, line_count)
