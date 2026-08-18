import copy
import os
import shutil
import subprocess
import tempfile
import heapq
from collections import defaultdict
from pathlib import Path
from subprocess import CalledProcessError
from tqdm import tqdm

from ..models.entry import Entry
from ..models.header import Header
from ..renderers.html_renderer import HTMLRenderer
from .html_page import HTMLPage
from ..utils import normalize

USING_ORJSON = False
try:
    import orjson
    def json_loads(line): return orjson.loads(line)
    def json_dumps(obj): return orjson.dumps(obj).decode('utf-8')
    USING_ORJSON = True
except ImportError:
    import json
    def json_loads(line): return json.loads(line)
    def json_dumps(obj): return json.dumps(obj)


TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

class KindleDict:
    def __init__(self, wiktionary_fp, lang_code, kindlegen_path):
        self.wiktionary_fp = wiktionary_fp
        self.lang_code = lang_code
        self.output_dir = self.ensure_unique_directory(f"outputs/KindleDictionary-{self.lang_code}")
        self.output_sub_dir = os.path.join(self.output_dir, "files")
        self.kindlegen_path = kindlegen_path

        self.entries = {}
        self.normalized_lemmas = defaultdict(set)
        self.entry_ids = {}
        self.line_count = None

    @staticmethod
    def ensure_unique_directory(path):
        if not os.path.exists(path): return path
        base, counter = path, 1
        while os.path.exists(f"{base} ({counter})"): counter += 1
        return f"{base} ({counter})"

    def init_dict_dir(self):
        os.makedirs(self.output_sub_dir, exist_ok=True)
        shutil.copy(TEMPLATES_DIR / "style.css", self.output_sub_dir)
        shutil.copy(TEMPLATES_DIR / "cover.png", self.output_sub_dir)

    @staticmethod
    def root_form(senses):
        if not senses: return None
        sense = senses[0]
        if "alt_of" in sense: return sense["alt_of"][0].get("word")
        if "form_of" in sense: return sense["form_of"][0].get("word")
        links = sense.get("links", [])
        if len(links) == 1 and len(links[0]) == 2 and links[0][1].endswith(f"#Latin"):
            root_word = links[0][0]
            for gloss in sense.get("glosses", []):
                if gloss.endswith(f" of {root_word}"): return root_word
        return None
    
    @staticmethod
    def get_header(json_entry):
        plain_word = json_entry.get("word", "")
        head_template = json_entry.get("head_templates", [{}])
        expansion = head_template[0].get('expansion', "")
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

    def get_addl_forms(self, alt_forms_dict, head_word, part_of_speech, seen_words=None):
        if seen_words is None: seen_words = set()
        seen_words.add(head_word)
        addl_forms = []
        stack = [(head_word, part_of_speech)]

        while stack:
            curr_word, curr_pos = stack.pop()
            # Fast O(1) Dictionary Lookup
            matching_items = alt_forms_dict.get(curr_word, [])
            
            for alt_pos, json_entry in matching_items:
                addl_forms.extend(self.preprocess_addl_forms(json_entry))
                sub_head_word = self.get_header(json_entry)
                
                # Check directly in the dictionary keys (O(1)) to decide if we append
                if sub_head_word in alt_forms_dict and sub_head_word not in seen_words:
                    seen_words.add(sub_head_word)
                    stack.append((sub_head_word, alt_pos))
        return addl_forms

    def make_sorted_path(self):
        base, ext = os.path.splitext(self.wiktionary_fp)
        return f"{base}(sorted){ext}"
    
    def sort_jsonl(self, chunk_size=200000):
        """Sorts JSONL file using an external merge sort to prevent disk I/O thrashing."""
        if not USING_ORJSON:
            print("Info: `orjson` not detected. Running with standard `json` (install `wiktionary-to-kindle[fast]` for speedups).")

        EXCLUDED_POS = {'suffix', 'character', 'prefix', 'symbol', 'interfix', 'infix', 'circumfix', 'punct'}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            chunk_files = []
            current_chunk = []
            alt_forms_dict = defaultdict(list)
            
            def write_chunk(chunk_data, chunk_index):
                chunk_data.sort(key=lambda item: (normalize(item[0], lowercase=True), normalize(item[0], lowercase=False)))
                chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}.jsonl")
                with open(chunk_path, 'w', encoding='utf-8') as out_c:
                    for _, _, line in chunk_data: out_c.write(line)
                return chunk_path

            with open(self.wiktionary_fp, 'r', encoding='utf-8') as f:
                file_size = f.seek(0, 2)
                f.seek(0)
                with tqdm(total=file_size, unit="B", unit_scale=True, desc="Chunking JSONL") as pbar:
                    self.line_count, chunk_index = 0, 0
                    while True:
                        pos = f.tell()
                        line = f.readline()
                        if not line:
                            if current_chunk: chunk_files.append(write_chunk(current_chunk, chunk_index))
                            break

                        pbar.update(f.tell() - pos)
                        obj = json_loads(line)

                        # Add this guard to drop non-Latin false positives
                        if obj.get("lang_code") != self.lang_code:
                            continue

                        word = normalize(obj["word"], lowercase=False)

                        part_of_speech = obj.get('pos')
                        
                        if part_of_speech not in EXCLUDED_POS and not word.startswith('-') and not word.endswith('-'):
                            header = self.get_header(obj)
                            root = self.root_form(obj.get("senses", []))
                            
                            if root is None:
                                current_chunk.append((header, part_of_speech, line))
                                self.line_count += 1
                                if len(current_chunk) >= chunk_size:
                                    chunk_files.append(write_chunk(current_chunk, chunk_index))
                                    current_chunk = []
                                    chunk_index += 1
                            else:
                                # Key only by root to drastically speed up processing during the merge
                                alt_forms_dict[root].append((part_of_speech, obj))
            
            output_path = self.make_sorted_path()
            with open(output_path, 'w', encoding='utf-8') as out_f:
                files = [open(cf, 'r', encoding='utf-8') for cf in chunk_files]
                
                def read_lines(file_obj):
                    for fl in file_obj:
                        obj = json_loads(fl)
                        word = normalize(self.get_header(obj), lowercase=True)
                        yield (word, obj.get('pos'), obj)

                merged_iter = heapq.merge(*[read_lines(f) for f in files], key=lambda x: (normalize(x[0], lowercase=True), normalize(x[0], lowercase=False)))
                
                with tqdm(total=self.line_count, unit="lines", unit_scale=True, desc="Merging Chunks") as pbar:
                    for word, pos, obj in merged_iter:
                        addl_forms = self.get_addl_forms(alt_forms_dict, word, pos)
                        if addl_forms:
                            if "forms" not in obj: obj["forms"] = []
                            obj["forms"].extend(addl_forms)
                        out_f.write(json_dumps(obj) + '\n')
                        pbar.update(1)

                for f in files: f.close()
            
            self.wiktionary_fp = output_path
    
    def add_entry_to_dictionary(self, entry, html_pages, descendant_langs, link_examples, recursive_senses, include_etymology):
        entry_filename = html_pages["main"].get_filename()
        self.entries.setdefault(entry.head_word, (entry.id_number, entry_filename))
        self.normalized_lemmas[normalize(entry.head_word, lowercase=True)].add(entry.id_number)
        self.entry_ids[entry.id_number] = entry_filename
        
        html_pages["main"].add_lines(HTMLRenderer.render_entry(entry, descendant_langs, link_examples, recursive_senses, include_etymology))
        if link_examples:
            html_pages["examples"].add_lines(HTMLRenderer.render_examples(entry, entry_filename))

    def make_opf(self, html_pages):
        entry_page_len = html_pages["main"].index
        inflection_page_len = html_pages["inflections"].index
        example_page_len = html_pages["examples"].index
        
        with open(TEMPLATES_DIR / "opf_header.txt", "r", encoding="utf-8") as f:
            html_lines = f.read().split('\n')
            
        for prefix, page_len in [("", entry_page_len), ("inf-", inflection_page_len), ("ex-", example_page_len)]:
            for page_num in range(page_len):
                html_lines.append(f'<item id="{prefix}page-{page_num}" href="{prefix}{page_num:04}.xhtml" media-type="application/xhtml+xml"/>')

        html_lines.extend(['</manifest>', '<spine>'])
        for prefix, page_len in [("", entry_page_len), ("inf-", inflection_page_len), ("ex-", example_page_len)]:
            for page_num in range(page_len):
                html_lines.append(f'<itemref idref="{prefix}page-{page_num}"/>')

        html_lines.extend(['</spine>', '</package>'])
        with open(os.path.join(self.output_sub_dir, "dictionary.opf"), "w", encoding="utf-8") as f:
            f.write('\n'.join(html_lines))
    
    def make_mobi(self):
        mobi_name = f"{self.lang_code}-wiktionary.mobi"
        try:
            subprocess.run([self.kindlegen_path, "dictionary.opf", "-o", mobi_name], cwd=self.output_sub_dir, check=True)
            shutil.move(os.path.join(self.output_sub_dir, mobi_name), os.path.join(self.output_dir, mobi_name))
        except CalledProcessError as e: 
            if e.returncode == 1:
                shutil.move(os.path.join(self.output_sub_dir, mobi_name), os.path.join(self.output_dir, mobi_name))
            else:
                print(f"Error compiling MOBI: {e}")
                
    def count_lines(self):
        with open(self.wiktionary_fp, "rb") as f: self.line_count = sum(1 for _ in f)

    def build_dictionary(self, max_page_len=5000, limit=None, descendant_langs=None, link_examples=True, recursive_senses=True, include_etymology=True):
        self.init_dict_dir()
        if limit is None:
            if self.line_count is None: self.count_lines()
            limit = self.line_count
        
        html_pages = {
            "main": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/'),
            "inflections": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/inf-'),
            "examples": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/ex-')
        }
        
        last_entry_id = 0
        all_inflections = defaultdict(list)

        with open(self.wiktionary_fp, "r", encoding="utf-8") as f:
            for line in tqdm(f, unit="lines", unit_scale=True, total=limit, desc="Building"):
                json_entry = json_loads(line)
                alt_id, alt_page = self.entries.get(json_entry.get("alt_of"), (None, None))
                entry = Entry(json_entry, last_entry_id + 1, alt_id, alt_page, html_pages["examples"].get_filename())
                
                for split_entry in entry.split():
                    last_entry_id += 1
                    new_id_str = f"i{last_entry_id}_1"
                    split_entry.id_number = last_entry_id
                    split_entry.id = new_id_str
                    
                    # Update nested Header objects for main entry rendering
                    if hasattr(split_entry, "main_header") and split_entry.main_header:
                        split_entry.main_header.id = new_id_str
                    if hasattr(split_entry, "headers") and split_entry.headers:
                        for h in split_entry.headers:
                            h.id = new_id_str

                    self.add_entry_to_dictionary(split_entry, html_pages, descendant_langs, link_examples, recursive_senses, include_etymology)
                    
                    for form, inflection in split_entry.inflected_forms.items():
                        norm_key = normalize(form, lowercase=True)
                        all_inflections[norm_key].append((split_entry, inflection))
                
                if len(self.entries) >= limit: break
        
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
                    inf_id_str = f"inf_{last_entry_id}"
                    
                    temp_entry = copy.copy(split_entry)
                    temp_entry.id_number = last_entry_id
                    temp_entry.id = inf_id_str
                    
                    # Copy and update nested Header objects so Jinja gets a unique ID
                    if hasattr(temp_entry, "main_header") and temp_entry.main_header:
                        temp_entry.main_header = copy.copy(temp_entry.main_header)
                        temp_entry.main_header.id = inf_id_str
                    if hasattr(temp_entry, "headers") and temp_entry.headers:
                        temp_entry.headers = [copy.copy(h) for h in temp_entry.headers]
                        for h in temp_entry.headers:
                            h.id = inf_id_str

                    temp_entry.inflected_forms = {inflection.form: inflection}
                    html_pages["inflections"].add_lines(
                        HTMLRenderer.render_inflections_html(temp_entry, 1)
                    )

        for title, page in html_pages.items(): page.write()
        self.make_opf(html_pages)
        self.make_mobi()