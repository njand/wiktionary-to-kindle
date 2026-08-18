from Entry import Entry
from Header import Header
from HTMLPage import HTMLPage
from utils import normalize

import shutil
import re
import os
import json
import subprocess
from subprocess import CalledProcessError
from collections import defaultdict
from tqdm import tqdm


class KindleDict:
    def __init__(self, wiktionary_fp, lang_code, kindlegen_path):
        self.wiktionary_fp = wiktionary_fp
        self.lang_code = lang_code

        self.output_dir = self.ensure_unique_directory(f"../outputs/KindleDictionary-{self.lang_code}")
        self.output_sub_dir = self.output_dir + "/files"
        
        self.kindlegen_path = kindlegen_path

        self.entries = {}
        self.normalized_lemmas = defaultdict(set)
        self.entry_ids = {}
        self.current_json = None
        self.current_entry = None
        self.line_count = None
    
    @staticmethod
    def ensure_unique_directory(path):
        """Ensure the given directory exists. If it exists, create a unique version with a numerical suffix."""
        if not os.path.exists(path):
            return path

        base, counter = path, 1
        while os.path.exists(f"{base} ({counter})"):
            counter += 1

        new_path = f"{base} ({counter})"
        return new_path
    
    def init_dict_dir(self, css_fp="../templates/style.css",
                      cover_fp="../templates/cover.png"):
        os.makedirs(self.output_sub_dir)
        shutil.copy(css_fp, self.output_sub_dir)
        shutil.copy(cover_fp, self.output_sub_dir)

    @staticmethod
    def root_form(senses):
        if len(senses) == 0:
            return 0

        sense = senses[0]

        if "alt_of" in sense:
            return sense["alt_of"][0].get("word")
        elif "form_of" in sense:
            return sense["form_of"][0].get("word")

        links = sense.get("links", [])
        if len(links) != 1:
            return None
        link = links[0]
        if len(link) != 2 or not link[1].endswith("#Latin"):
            return None
        root_word = link[0]

        for gloss in sense.get("glosses", []):
            if gloss.endswith(f" of {root_word}"):
                return root_word

        return None
    
    @staticmethod
    def get_header(json_entry):
        plain_word = json_entry.get("word", "")
        
        if "head_templates" not in json_entry:
            header = Header(plain_word, "", num_headers=1)
        head_template = json_entry.get("head_templates", [{}])
        expansion = head_template[0].get('expansion', "")
        header = Header(plain_word, expansion, num_headers=1)

        return header.head_word

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

    def get_addl_forms(self, f, alt_positions, head_word, part_of_speech, seen_words=None, verbose=False):
        if seen_words is None:
            seen_words = set()
        
        seen_words.add(head_word)
        addl_forms = []
        stack = [(head_word, part_of_speech)]

        while stack:
            curr_word, curr_pos = stack.pop()
            
            if verbose:
                print("HEADWORD:", curr_word)
                print("POS:", curr_pos)

            for pos in alt_positions.get((curr_word, curr_pos), []):
                f.seek(pos)
                line = f.readline()
                json_entry = json.loads(line)

                if verbose:
                    print(self.preprocess_addl_forms(json_entry))

                addl_forms.extend(self.preprocess_addl_forms(json_entry))

                sub_head_word = self.get_header(json_entry)
                if (sub_head_word, curr_pos) in alt_positions and sub_head_word not in seen_words:
                    seen_words.add(sub_head_word)
                    stack.append((sub_head_word, curr_pos))

        return addl_forms

    def make_sorted_path(self) -> str:
        """
        Given the input file path, return a path for the sorted version.
        Example: '../data/filtered_la.jsonl' -> '../data/filtered_la(sorted).jsonl'
        """
        base, ext = os.path.splitext(self.wiktionary_fp)
        return f"{base}(sorted){ext}"
    
    def sort_jsonl(self):
        """Sorts large JSONL file by normalized "word", to allow for more efficient processing."""
        EXCLUDED_POS = [
            'suffix',
            'character',
            'prefix',
            'symbol',
            'interfix',
            'infix',
            'circumfix',
            'punct'
        ]

        # First pass: Extract and normalize words, storing positions
        main_positions = defaultdict(list)
        alt_positions = defaultdict(list)  # store other word forms separately to add them to the main entries
        
        with open(self.wiktionary_fp, 'r', encoding='utf-8') as f:
            file_size = f.seek(0, 2)  # Move to end to get file size
            f.seek(0)  # Reset file pointer to the beginning

            with tqdm(total=file_size, unit="B", unit_scale=True, desc="Reading unsorted JSONL") as pbar:
                self.line_count = 0
                while True:
                    pos = f.tell()  # Get current file position
                    
                    line = f.readline()
                    if not line:
                        break  # Stop if end of file is reached
                    obj = json.loads(line)
                    word = normalize(obj["word"], lowercase=False)
                    header = self.get_header(obj)
                    part_of_speech = obj.get('pos')
                    
                    if (
                        part_of_speech in EXCLUDED_POS
                        or word.startswith('-')
                        or word.endswith('-')
                       ):
                        pass  # Skip this entry
                    else:
                        root = self.root_form(obj.get("senses", []))
                        
                        if root is None:
                            main_positions[(header, part_of_speech)].append(pos)
                            self.line_count += 1
                        else:
                            alt_positions[(root, part_of_speech)].append(pos)

                    pbar.update(f.tell() - pos)  # Update progress bar with bytes read
        
        output_path = self.make_sorted_path()
        
        # Second pass: Stream through file and write in sorted order
        with open(self.wiktionary_fp, 'r', encoding='utf-8') as f, open(output_path, 'w', encoding='utf-8') as out_f:
            with tqdm(total=self.line_count, unit="lines", unit_scale=True, desc="Writing sorted lines") as pbar:
                for (word, part_of_speech), positions in sorted(main_positions.items(),
                                              key=lambda item: (normalize(item[0][0], lowercase=True),
                                                                normalize(item[0][0], lowercase=False))):
                    addl_forms = self.get_addl_forms(f, alt_positions, word, part_of_speech)

                    for pos in positions:
                        f.seek(pos)  # Jump to the stored position
                        line = f.readline()
                        
                        if len(addl_forms) > 0:
                            json_entry = json.loads(line)
                            if "forms" not in json_entry:
                                json_entry["forms"] = []
                            json_entry["forms"].extend(addl_forms)
                            line = json.dumps(json_entry) + '\n'
                            
                        out_f.write(line)  # Write the line

                        pbar.update(1)
        
        self.wiktionary_fp = output_path
    
    def add_entry_to_dictionary(self, entry, html_pages, descendant_langs=None, link_examples=True,
                                recursive_senses=True, include_etymology=True):
        entry_filename = html_pages["main"].get_filename()
        self.entries.setdefault(entry.head_word, (entry.id_number, entry_filename))
        self.normalized_lemmas[normalize(entry.head_word, lowercase=True)].add(entry.id_number)
        self.entry_ids[entry.id_number] = entry_filename
        
        html_pages["main"].add_lines(entry.to_html(descendant_langs, link_examples, recursive_senses, include_etymology))
        
        if link_examples:
            entry_page = html_pages["main"].get_filename()
            html_pages["examples"].add_lines(entry.examples_html(entry_page))

    def count_lines(self):
        with open(self.wiktionary_fp, "rb") as f:
            self.line_count = sum(1 for _ in f)

    def make_opf(self, html_pages, header_fp="../templates/opf_header.txt", output_file="dictionary.opf"):
        entry_page_len = html_pages["main"].index
        inflection_page_len = html_pages["inflections"].index
        example_page_len = html_pages["examples"].index
        
        html_lines = open(header_fp, "r", encoding="utf-8").read().split('\n')
        
        for prefix, page_len in [("", entry_page_len), ("inf-", inflection_page_len), ("ex-", example_page_len)]:
            for page_num in range(page_len):
                html_lines.append(f'<item id="{prefix}page-{page_num}" href="{prefix}{page_num:04}.xhtml" media-type="application/xhtml+xml"/>')

        html_lines.append('</manifest>')
        html_lines.append('<spine>')
        
        for prefix, page_len in [("", entry_page_len), ("inf-", inflection_page_len), ("ex-", example_page_len)]:
            for page_num in range(page_len):
                html_lines.append(f'<itemref idref="{prefix}page-{page_num}"/>')

        html_lines.append('</spine>')
        html_lines.append('</package>')
        
        output_fp = os.path.join(self.output_dir, "files", output_file)
        with open(output_fp, "w", encoding="utf-8") as f:
            for lines in html_lines:
                f.write(lines)
                f.write('\n')
    
    def make_inflections_entries(self, html_pages, inflection_max_senses, limit):
        # TODO: Combine together multiple derivations into a single entry
        """
        Write inflections for exact matches to a form in a preceding entry,
        and also backfill the first occurrence, using byte offsets for efficiency.
        """
        previous_forms = {}   # form -> (byte_offset, id_number)
        created_forms = set() # forms we've already output HTML for

        def write_inflection(entry, form, norm_form, verbose=False):
            """Write inflection HTML for the given form in the given entry."""
            inflection = entry.inflected_forms.get(form)
            if inflection:
                html_pages["inflections"].add_lines(inflection.to_html(inflection_max_senses))
                created_forms.add(norm_form)
#                 if verbose:
#                     print(f"Writing form {form}.")

        def backfill_form(form, norm_form, file_obj, verbose=False):
            """Go back to the first occurrence and write its inflection if needed."""
            if norm_form not in previous_forms or norm_form in created_forms:
                if verbose:
                    print(f"Form '{form}' doesn't need to be backfilled.")
                return
            prev_offset, prev_id = previous_forms[norm_form]
            cur_pos = file_obj.tell()
            file_obj.seek(prev_offset)
            old_line = file_obj.readline()
            old_entry_json = json.loads(old_line)
            old_entry = Entry(old_entry_json, prev_id, None, None, None,
                              entry_ids=self.entry_ids, add_tags=True)
#             if verbose:
#                 print(f"Backfill head: {old_entry.head_word}")
                
            found_form = False
            for old_split in old_entry.split():
                for inf_form in old_split.inflected_forms:
                    if norm_form == normalize(inf_form, lowercase=True):
#                         if verbose:
#                             print(f"Found original form")
                            
                        write_inflection(old_split, inf_form, norm_form, verbose)
#                         if verbose:
#                             print(f"Wrote {form}")
                        
                        found_form = True
                        break
                if found_form:
                    break
#                 if verbose:
#                     print(f"{form} not in old_split")
            file_obj.seek(cur_pos)

        with open(self.wiktionary_fp, "r", encoding="utf-8") as f:
            last_entry_id = 0
            for _ in tqdm(range(limit), unit="lines", unit_scale=True, total=limit,
                          desc="Ambiguous inflections"):
                byte_offset = f.tell()
                line = f.readline()
                if not line:
                    break

                json_entry = json.loads(line)
                self.current_json = json_entry

                entry = Entry(json_entry, last_entry_id + 1, alt_id=None, alt_page=None,
                              examples_page=None, entry_ids=self.entry_ids, add_tags=True)
                self.current_entry = entry
                                
                entry_prev_forms = {}
                for split_entry in entry.split():
                    last_entry_id = split_entry.id_number

                    for form in split_entry.all_forms:
                        norm_form = normalize(form, lowercase=True)
                        verbose = False
#                         if norm_form in ["reducis", "magno", "ripam"]:
#                             verbose = True
#                         else:
#                             verbose = False
                        
                        lemma_ids = self.normalized_lemmas.get(norm_form, None)
#                         if verbose:
#                             print(f"\n{form} --> {norm_form}")
#                             print("lemma_ids:", lemma_ids)
                        if lemma_ids and last_entry_id in lemma_ids:
#                             if verbose:
#                                 print(f"Skipping backfilling for lemma_id: {last_entry_id}")
                            continue
                        
                        is_duplicate = norm_form in previous_forms or lemma_ids is not None

                        if is_duplicate:
#                             if verbose:
#                                 print(f"duplicate form: {norm_form} ({form}) < {split_entry.head_word}")
                            backfill_form(form, norm_form, f, verbose)
                            write_inflection(split_entry, form, norm_form, verbose)

                        if norm_form not in previous_forms:
#                             if verbose:
#                                 print(f"form: {norm_form} ({form}) not in previous forms")
                            entry_prev_forms[norm_form] = (byte_offset, entry.id_number)
                previous_forms.update(entry_prev_forms)

    def make_inflection_ids_unique(self):
        """
        Normalize <idx:entry ... id="..."> across all .xhtml files for inflected forms:
        - Guarantee uniqueness across all files
        - Stable order: files sorted by path, entries by appearance
        - Always add a numeric suffix (_0, _1, ...) for uniqueness in a single pass.
        """
        entry_pattern = re.compile(r'(<idx:entry[^>]*\bid=["\'])([^"\']+)(["\'])', re.IGNORECASE)
        counters = defaultdict(int)

        xhtml_files = sorted(
            os.path.join(root, fname)
            for root, _, files in os.walk(self.output_sub_dir)
            for fname in files if fname.startswith("inf-") and fname.endswith(".xhtml")
        )

        for path in xhtml_files:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            def repl(match):
                base = match.group(2)
                new_id = f"{base}_{counters[base]}"
                counters[base] += 1
                return f"{match.group(1)}{new_id}{match.group(3)}"

            new_content = entry_pattern.sub(repl, content)

            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)

    def make_mobi(self):
        opf_path = "dictionary.opf"
        mobi_name = f"{self.lang_code}-wiktionary.mobi"
        try:
            subprocess.run([
                self.kindlegen_path,
                opf_path,
                "-o", mobi_name
            ], cwd=self.output_sub_dir, check=True)
            
            shutil.move(os.path.join(self.output_sub_dir, mobi_name), os.path.join(self.output_dir, mobi_name))
        except CalledProcessError as e:
            print(e)
        
    def build_dictionary(self, max_page_len=5000, limit=None, descendant_langs=None, inflection_max_senses=1,
                         link_examples=True, recursive_senses=True, include_etymology=True, disambiguate_inflections=True):
        self.init_dict_dir()

        if limit is None:
            if self.line_count is None:
                self.count_lines()
            limit = self.line_count
        
        html_pages = {
            "main": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/'),
            "inflections": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/inf-'),
            "examples": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/ex-')
        }
        
        last_entry_id = 0
        with open(self.wiktionary_fp, "r", encoding="utf-8") as f:
            for i, line in tqdm(enumerate(f), unit="lines", unit_scale=True, total=limit, desc="Building dictionary"):
                json_entry = json.loads(line)
                self.current_json = json_entry
                
                alt_id = alt_page = None
                if "alt_of" in json_entry:
                    alt_id, alt_page = self.entries.get(json_entry["alt_of"], (None, None))
                
                examples_page = html_pages["examples"].get_filename()

                entry = Entry(json_entry, last_entry_id+1, alt_id, alt_page, examples_page)
                self.current_entry = entry
                for split_entry in entry.split():
                    self.add_entry_to_dictionary(split_entry, html_pages, descendant_langs, link_examples,
                                                 recursive_senses, include_etymology)
                    last_entry_id = split_entry.id_number
                
                if len(self.entries) >= limit:
                    break
        
        if disambiguate_inflections:
            self.make_inflections_entries(html_pages, inflection_max_senses, limit=i+1)
        
        for title, page in html_pages.items():
            page.write()

        if disambiguate_inflections:
            self.make_inflection_ids_unique()

        self.make_opf(html_pages)
        
        print("Writing mobi...")
        self.make_mobi()
        print("Done!")
