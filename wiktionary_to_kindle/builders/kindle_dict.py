import heapq
import json
import os
import shutil
import subprocess
import tempfile
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
from subprocess import CalledProcessError

from tqdm import tqdm

from ..models.entry import Entry
from ..models.header import Header
from ..renderers.html_renderer import HTMLRenderer
from ..utils import TEMPLATES, form_of_root, normalize, remove_breves
from .html_page import HTMLPage

USING_ORJSON = False
try:
    import orjson

    def json_loads(line):
        return orjson.loads(line)

    def json_dumps(obj):
        return orjson.dumps(obj).decode("utf-8")

    USING_ORJSON = True
except ImportError:

    def json_loads(line):
        return json.loads(line)

    def json_dumps(obj):
        return json.dumps(obj)


# Bump when sort_jsonl's output changes, so cached sorted files are rebuilt
SORT_VERSION = 2


class KindleDict:
    def __init__(self, wiktionary_fp, lang_code, kindlegen_path):
        self.wiktionary_fp = wiktionary_fp
        self.lang_code = lang_code
        self.output_dir = self.ensure_unique_directory(
            f"outputs/KindleDictionary-{self.lang_code}"
        )
        self.output_sub_dir = os.path.join(self.output_dir, "files")
        self.kindlegen_path = kindlegen_path

        self.entries = {}
        self.normalized_lemmas = defaultdict(set)
        self.entry_ids = {}
        self.line_count = None

    @staticmethod
    def ensure_unique_directory(path):
        if not os.path.exists(path):
            return path
        base, counter = path, 1
        while os.path.exists(f"{base} ({counter})"):
            counter += 1
        return f"{base} ({counter})"

    def init_dict_dir(self):
        os.makedirs(self.output_sub_dir, exist_ok=True)
        for name in ("style.css", "cover.png"):
            data = TEMPLATES.joinpath(name).read_bytes()
            Path(self.output_sub_dir, name).write_bytes(data)

    @staticmethod
    def root_form(senses):
        """Return the lemma this entry only points to, or None if any sense defines it."""
        roots = [form_of_root(sense) for sense in senses]
        if not roots or None in roots:
            return None
        return roots[0]

    @staticmethod
    def get_header(json_entry):
        plain_word = json_entry.get("word", "")
        head_template = json_entry.get("head_templates", [{}])
        expansion = head_template[0].get("expansion", "")
        return Header(plain_word, expansion, num_headers=1).head_word

    @staticmethod
    def preprocess_addl_forms(json_entry):
        sense = json_entry.get("senses", [{}])[0]
        tags = sense.get("tags", [])
        processed_forms = []
        for form in json_entry.get("forms", []):
            if form.get("tags") == ["canonical"]:
                form["tags"] = tags
            processed_forms.append(form)
        return processed_forms

    def get_addl_forms(
        self, alt_forms_dict, head_key, part_of_speech, lemma_pos, promoted
    ):
        """Collect forms of entries that only point at head_key (inflections, comparatives,
        alternative spellings), following chains such as a form of an alternative form."""
        seen_keys = {head_key}
        addl_forms = []
        stack = [head_key]

        while stack:
            curr_key = stack.pop()
            for alt_pos, alt_header, json_entry in alt_forms_dict.get(curr_key, []):
                if id(json_entry) in promoted:
                    continue
                # Leave a direct pointer to a same-POS homograph lemma if one exists
                if (
                    curr_key == head_key
                    and alt_pos != part_of_speech
                    and alt_pos in lemma_pos[head_key]
                ):
                    continue
                addl_forms.extend(self.preprocess_addl_forms(json_entry))

                sub_key = remove_breves(alt_header)
                if sub_key in alt_forms_dict and sub_key not in seen_keys:
                    seen_keys.add(sub_key)
                    stack.append(sub_key)
        return addl_forms

    def promote_orphans(self, alt_forms_dict, lemma_pos):
        """Return pointer entries whose chain never reaches a lemma, so they become entries
        themselves instead of being dropped. Promoted entries can in turn act as roots."""
        reached = set()

        def reach(key):
            stack = [key]
            while stack:
                for _pos, alt_header, obj in alt_forms_dict.get(stack.pop(), []):
                    if id(obj) not in reached:
                        reached.add(id(obj))
                        stack.append(remove_breves(alt_header))

        for key in list(lemma_pos):
            reach(key)

        orphans = []
        for key in sorted(alt_forms_dict):
            for alt_pos, alt_header, obj in alt_forms_dict[key]:
                if id(obj) in reached:
                    continue
                lemma_pos[remove_breves(alt_header)].add(alt_pos)
                orphans.append((alt_header, alt_pos, obj))
                reached.add(id(obj))
                reach(remove_breves(alt_header))
        return orphans

    def make_sorted_path(self):
        base, ext = os.path.splitext(self.wiktionary_fp)
        return f"{base}(sorted){ext}"

    def sorted_cache_meta(self):
        stat = os.stat(self.wiktionary_fp)
        return {
            "sort_version": SORT_VERSION,
            "source_size": stat.st_size,
            "source_mtime_ns": stat.st_mtime_ns,
        }

    def sort_jsonl(self, chunk_size=200000, force=False):
        """Sorts JSONL file using an external merge sort to prevent disk I/O thrashing.

        The result is cached beside the input; it is reused while the input file and
        SORT_VERSION are unchanged, unless force is set.
        """
        output_path = self.make_sorted_path()
        meta_path = Path(output_path + ".meta.json")
        meta = self.sorted_cache_meta()
        cached = (
            not force
            and os.path.exists(output_path)
            and meta_path.exists()
            and json.loads(meta_path.read_text(encoding="utf-8")) == meta
        )
        if cached:
            print(f"Reusing sorted file {output_path} (pass --resort to rebuild it)")
            self.wiktionary_fp = output_path
            return

        print("Sorting JSONL file...")
        if not USING_ORJSON:
            print(
                "Info: `orjson` not detected. Running with standard `json` (install `wiktionary-to-kindle[fast]` for speedups)."
            )

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

        with tempfile.TemporaryDirectory() as temp_dir:
            chunk_files = []
            current_chunk = []
            # Keyed by macronized headword: Wiktionary's form_of/alt_of targets keep macrons
            alt_forms_dict = defaultdict(list)
            lemma_pos = defaultdict(set)

            def write_chunk(chunk_data, chunk_index):
                chunk_data.sort(
                    key=lambda item: (
                        normalize(item[0], lowercase=True),
                        normalize(item[0], lowercase=False),
                    )
                )
                chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}.jsonl")
                with open(chunk_path, "w", encoding="utf-8") as out_c:
                    for _, _, line in chunk_data:
                        out_c.write(line)
                return chunk_path

            with open(self.wiktionary_fp, "r", encoding="utf-8") as f:
                file_size = f.seek(0, 2)
                f.seek(0)
                with tqdm(
                    total=file_size, unit="B", unit_scale=True, desc="Chunking JSONL"
                ) as pbar:
                    self.line_count, chunk_index = 0, 0
                    while True:
                        pos = f.tell()
                        line = f.readline()
                        if not line:
                            if current_chunk:
                                chunk_files.append(
                                    write_chunk(current_chunk, chunk_index)
                                )
                            break

                        pbar.update(f.tell() - pos)
                        obj = json_loads(line)

                        if obj.get("lang_code") != self.lang_code:
                            continue

                        word = normalize(obj["word"], lowercase=False)
                        part_of_speech = obj.get("pos")

                        if (
                            part_of_speech not in EXCLUDED_POS
                            and not word.startswith("-")
                            and not word.endswith("-")
                        ):
                            header = self.get_header(obj)
                            root = self.root_form(obj.get("senses", []))

                            if root is None:
                                lemma_pos[remove_breves(header)].add(part_of_speech)
                                current_chunk.append((header, part_of_speech, line))
                                self.line_count += 1
                                if len(current_chunk) >= chunk_size:
                                    chunk_files.append(
                                        write_chunk(current_chunk, chunk_index)
                                    )
                                    current_chunk = []
                                    chunk_index += 1
                            else:
                                alt_forms_dict[remove_breves(root)].append(
                                    (part_of_speech, header, obj)
                                )

            orphans = self.promote_orphans(alt_forms_dict, lemma_pos)
            promoted = {id(obj) for _, _, obj in orphans}
            if orphans:
                chunk_files.append(
                    write_chunk(
                        [(h, p, json_dumps(o) + "\n") for h, p, o in orphans],
                        chunk_index + 1,
                    )
                )
                self.line_count += len(orphans)

            def read_lines(file_obj):
                for fl in file_obj:
                    obj = json_loads(fl)
                    header = self.get_header(obj)
                    # Compute exact sort keys once per line to match write_chunk logic
                    yield (
                        normalize(header, lowercase=True),
                        normalize(header, lowercase=False),
                        header,
                        obj.get("pos"),
                        obj,
                    )

            with ExitStack() as stack:
                out_f = stack.enter_context(open(output_path, "w", encoding="utf-8"))
                files = [
                    stack.enter_context(open(cf, "r", encoding="utf-8"))
                    for cf in chunk_files
                ]

                merged_iter = heapq.merge(
                    *(read_lines(f) for f in files),
                    key=lambda x: (x[0], x[1]),
                )

                with tqdm(
                    total=self.line_count,
                    unit="lines",
                    unit_scale=True,
                    desc="Merging Chunks",
                ) as pbar:
                    for _lower_word, _raw_word, header, pos, obj in merged_iter:
                        if addl_forms := self.get_addl_forms(
                            alt_forms_dict,
                            remove_breves(header),
                            pos,
                            lemma_pos,
                            promoted,
                        ):
                            obj.setdefault("forms", []).extend(addl_forms)

                        out_f.write(json_dumps(obj) + "\n")
                        pbar.update(1)

        # Written last, so an interrupted sort is never mistaken for a finished one
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        self.wiktionary_fp = output_path

    def add_entry_to_dictionary(
        self,
        entry,
        html_pages,
        descendant_langs,
        recursive_senses,
        include_etymology,
    ):
        """Render entry and index it; return False, indexing nothing, if it has no senses."""
        lines = HTMLRenderer.render_entry(
            entry,
            descendant_langs,
            recursive_senses,
            include_etymology,
        )
        if not lines:
            return False

        entry_filename = html_pages["main"].get_filename()
        self.entries.setdefault(entry.head_word, (entry.id_number, entry_filename))
        self.normalized_lemmas[normalize(entry.head_word, lowercase=True)].add(
            entry.id_number
        )
        self.entry_ids[entry.id_number] = entry_filename

        html_pages["main"].add_lines(lines)
        return True

    def make_opf(self, html_pages):
        entry_page_len = html_pages["main"].index
        inflection_page_len = html_pages["inflections"].index

        html_lines = TEMPLATES.joinpath("opf_header.txt").read_text("utf-8").split("\n")

        for prefix, page_len in [
            ("", entry_page_len),
            ("inf-", inflection_page_len),
        ]:
            for page_num in range(page_len):
                html_lines.append(
                    f'<item id="{prefix}page-{page_num}" href="{prefix}{page_num:04}.xhtml" media-type="application/xhtml+xml"/>'
                )

        html_lines.extend(["</manifest>", "<spine>"])
        for prefix, page_len in [
            ("", entry_page_len),
            ("inf-", inflection_page_len),
        ]:
            for page_num in range(page_len):
                html_lines.append(f'<itemref idref="{prefix}page-{page_num}"/>')

        html_lines.extend(
            [
                "</spine>",
                "<guide>",
                '    <reference type="index" title="Dictionary" href="0000.xhtml"/>',
                "</guide>",
                "</package>",
            ]
        )
        with open(
            os.path.join(self.output_sub_dir, "dictionary.opf"), "w", encoding="utf-8"
        ) as f:
            f.write("\n".join(html_lines))

    def make_mobi(self):
        mobi_name = f"{self.lang_code}-wiktionary.mobi"
        src_path = os.path.join(self.output_sub_dir, mobi_name)
        dst_path = os.path.join(self.output_dir, mobi_name)

        try:
            subprocess.run(
                [self.kindlegen_path, "dictionary.opf", "-o", mobi_name],
                cwd=self.output_sub_dir,
                check=True,
            )
            if os.path.exists(src_path):
                shutil.move(src_path, dst_path)
        except CalledProcessError as e:
            if os.path.exists(src_path):
                shutil.move(src_path, dst_path)
            else:
                print(
                    f"Error compiling MOBI (exit code {e.returncode}). No binary generated."
                )
                raise

    def count_lines(self):
        with open(self.wiktionary_fp, "rb") as f:
            self.line_count = sum(1 for _ in f)

    def build_dictionary(
        self,
        max_page_len=5000,
        limit=None,
        descendant_langs=None,
        recursive_senses=True,
        include_etymology=True,
    ):
        self.init_dict_dir()
        if limit is None:
            if self.line_count is None:
                self.count_lines()
            limit = self.line_count

        html_pages = {
            "main": HTMLPage(
                max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + "/"
            ),
            "inflections": HTMLPage(
                max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + "/inf-"
            ),
        }

        last_entry_id = 0
        all_inflections = defaultdict(list)

        with open(self.wiktionary_fp, "r", encoding="utf-8") as f:
            for line in tqdm(
                f, unit="lines", unit_scale=True, total=limit, desc="Building"
            ):
                json_entry = json_loads(line)
                alt_id, alt_page = self.entries.get(
                    json_entry.get("alt_of"), (None, None)
                )
                entry = Entry(json_entry, last_entry_id + 1, alt_id, alt_page)

                for split_entry in entry.split():
                    last_entry_id += 1
                    split_entry.id_number = last_entry_id

                    if not self.add_entry_to_dictionary(
                        split_entry,
                        html_pages,
                        descendant_langs,
                        recursive_senses,
                        include_etymology,
                    ):
                        continue

                    for form, inflection in split_entry.inflected_forms.items():
                        norm_key = normalize(form, lowercase=True)
                        all_inflections[norm_key].append((split_entry, inflection))

                if len(self.entries) >= limit:
                    break

        # Render standalone inflection entries only for ambiguous cases
        for norm_form, inflection_list in all_inflections.items():
            is_headword = norm_form in self.normalized_lemmas
            is_multi_parent = len(inflection_list) > 1

            if is_headword or is_multi_parent:
                seen_pairs = set()
                for split_entry, inflection in inflection_list:
                    pair_key = (split_entry.id_number, inflection.form)
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    last_entry_id += 1
                    html_pages["inflections"].add_lines(
                        HTMLRenderer.render_inflection(
                            inflection, f"inf_{last_entry_id}", self.entry_ids
                        )
                    )

        for page in html_pages.values():
            page.write()
        self.make_opf(html_pages)
        self.make_mobi()
