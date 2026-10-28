import heapq
import json
import os
import shutil
import subprocess
import tempfile
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError

from tqdm import tqdm

from ..models.entry import Entry
from ..models.header import Header
from ..renderers.html_renderer import HTMLRenderer, format_gloss
from ..utils import (
    TEMPLATES,
    form_of_root,
    lookup_spellings,
    normalize,
    remove_breves,
)
from .forms import enrich_forms
from .html_page import HTMLPage
from .label_resolver import LabelResolver

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
SORT_VERSION = 5


@dataclass
class CardRow:
    """One entry as a disambiguation card lists it."""

    head: str
    pos: str | None
    parses: list[str]
    gloss: str
    id: int
    page: str = ""


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
        # Many pointer pages (innocentum, CON) list no forms: their headword is the only one
        header = KindleDict.get_header(json_entry)
        if all(form.get("form") != header for form in processed_forms):
            processed_forms.insert(0, {"form": header, "tags": tags})
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

    @staticmethod
    def rekey_plain_roots(alt_forms_dict, known):
        """File pointers whose target is no headword under the headword with its letters, so
        they merge like any other pointer: the target is often a page title without macrons
        ("alternative form of iuro" for iūrō), sometimes macronized otherwise (acontīzō for
        acontizō). known maps every headword to its parts of speech. When several headwords
        have those letters (latus, lātus), the one with the pointer's part of speech is taken,
        if one is."""
        by_letters = defaultdict(list)
        for header in known:
            by_letters[normalize(header)].append(header)

        for key in [k for k in alt_forms_dict if k not in known]:
            candidates = by_letters.get(normalize(key), [])
            if not candidates:
                continue
            stay = []
            for pointer in alt_forms_dict.pop(key):
                matches = candidates
                if len(matches) > 1:
                    matches = [h for h in candidates if pointer[0] in known[h]]
                if len(matches) == 1:
                    alt_forms_dict[matches[0]].append(pointer)
                else:
                    stay.append(pointer)
            if stay:
                alt_forms_dict[key] = stay

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

        # Promote the top of each chain first, so the forms that point at an orphan
        # (acontizante at acontizāns) merge into it instead of becoming orphans too
        pointer_keys = {
            remove_breves(alt_header)
            for pointers in alt_forms_dict.values()
            for _pos, alt_header, _obj in pointers
        }
        orphans = []
        for tops_only in (True, False):  # the second pass catches cycles
            for key in sorted(alt_forms_dict):
                if tops_only and key in pointer_keys:
                    continue
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
            # Every headword, without breves -> its parts of speech
            known = defaultdict(set)

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
                            known[remove_breves(header)].add(part_of_speech)

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

            self.rekey_plain_roots(alt_forms_dict, known)
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
                        addl_forms = self.get_addl_forms(
                            alt_forms_dict,
                            remove_breves(header),
                            pos,
                            lemma_pos,
                            promoted,
                        )
                        if "forms" in obj or addl_forms:
                            obj["forms"] = enrich_forms(
                                obj.get("forms", []), known, addl_forms
                            )

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
        orth=None,
        iforms=None,
    ):
        """Render entry and index it; return False, indexing nothing, if it has no senses."""
        lines = HTMLRenderer.render_entry(
            entry,
            descendant_langs,
            recursive_senses,
            include_etymology,
            orth,
            iforms,
        )
        if not lines:
            return False

        entry_filename = html_pages["main"].get_filename()
        self.entries.setdefault(entry.head_word, (entry.id_number, entry_filename))
        self.entry_ids[entry.id_number] = entry_filename

        html_pages["main"].add_lines(lines)
        return True

    def make_opf(self, html_pages):
        entry_page_len = html_pages["main"].index
        card_page_len = html_pages["cards"].index

        html_lines = TEMPLATES.joinpath("opf_header.txt").read_text("utf-8").split("\n")

        for prefix, page_len in [
            ("", entry_page_len),
            ("card-", card_page_len),
        ]:
            for page_num in range(page_len):
                html_lines.append(
                    f'<item id="{prefix}page-{page_num}" href="{prefix}{page_num:04}.xhtml" media-type="application/xhtml+xml"/>'
                )

        html_lines.extend(["</manifest>", "<spine>"])
        for prefix, page_len in [
            ("", entry_page_len),
            ("card-", card_page_len),
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

    def read_entries(self, limit, desc):
        """Yield (entry, size) for the dump's entries that render, numbered 1, 2, ... in
        file order. size is the JSON length without the inflection table, a rough measure
        of how much Wiktionary says about the word (a verb's table would dwarf it)."""
        entry_id = 0
        with open(self.wiktionary_fp, "r", encoding="utf-8") as f:
            for line in tqdm(f, unit="lines", unit_scale=True, total=limit, desc=desc):
                json_entry = json_loads(line)
                alt_id, alt_page = self.entries.get(
                    json_entry.get("alt_of"), (None, None)
                )
                entry = Entry(json_entry, entry_id + 1, alt_id, alt_page)
                if not entry.valid_pairs():
                    continue
                entry_id += 1
                yield entry, len(line) - len(json_dumps(json_entry.get("forms", [])))
                if entry_id >= limit:
                    break

    @staticmethod
    def card_rows(entry, cards):
        """List entry on each of its cards: its headword, and the parses of the forms that
        were tapped. A verb can be on hundreds of cards, so its forms are indexed once."""
        inflections = sorted(entry.inflected_forms.items(), key=lambda kv: kv[1])
        forms_of = defaultdict(list)  # label -> indexes into inflections
        for i, (form, _inflection) in enumerate(inflections):
            for label in lookup_spellings(form):
                forms_of[label].append(i)
        parses_of = [
            [str(tag) for tag in sorted(inflection.morph_tags)]
            for _form, inflection in inflections
        ]
        block, header = entry.valid_pairs()[0]
        gloss = format_gloss(next(iter(block.senses.values())))

        rows = {}
        for card in cards:
            reached = card.reached[entry.id_number]
            indexes = sorted({i for label in reached for i in forms_of.get(label, [])})
            parses = [p for i in indexes for p in parses_of[i] if p]
            rows[card.id_number] = CardRow(
                head=header.head_word,
                pos=entry.pos,
                parses=list(dict.fromkeys(parses)),
                gloss=gloss,
                id=entry.id_number,
            )
        return rows

    def build_dictionary(
        self,
        max_page_len=5000,
        limit=None,
        descendant_langs=None,
        recursive_senses=True,
        include_etymology=True,
    ):
        """Index every entry's labels, give each spelling one owner (an entry or a
        disambiguation card, see label_resolver), then render entries and cards."""
        self.init_dict_dir()
        if limit is None:
            if self.line_count is None:
                self.count_lines()
            limit = self.line_count

        resolver = LabelResolver()
        for entry, size in self.read_entries(limit, "Indexing labels"):
            resolver.add(
                entry.id_number, entry.head_word, entry.all_forms, size, entry.pos
            )
        cards = resolver.resolve()

        cards_of = defaultdict(list)
        for card in cards:
            for owner in card.owners:
                cards_of[owner].append(card)
        rows = defaultdict(dict)  # card id -> entry id -> CardRow

        html_pages = {
            "main": HTMLPage(
                max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + "/"
            ),
            "cards": HTMLPage(
                max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + "/card-"
            ),
        }

        for entry, _size in self.read_entries(limit, "Building"):
            orth, iforms = resolver.entry_labels(
                entry.id_number, entry.head_word, sorted(entry.all_forms)
            )
            self.add_entry_to_dictionary(
                entry,
                html_pages,
                descendant_langs,
                recursive_senses,
                include_etymology,
                orth,
                iforms,
            )
            if entry_cards := cards_of.pop(entry.id_number, []):
                for card_id, row in self.card_rows(entry, entry_cards).items():
                    rows[card_id][entry.id_number] = row

        for card in cards:
            card_rows = []
            for owner in card.owners:
                row = rows[card.id_number][owner]
                row.page = self.entry_ids.get(owner, "")
                card_rows.append(row)
            html_pages["cards"].add_lines(HTMLRenderer.render_card(card, card_rows))

        for page in html_pages.values():
            page.write()
        self.make_opf(html_pages)
        self.make_mobi()
