"""Cut a small, self-consistent sample out of a full filtered dump for fast development builds.

Lemmas are picked by a stable hash of their headword (so the same lemmas come out every time),
plus any word named in an include list. Every form-of / alt-of entry whose chain leads to a
picked lemma comes along, so merges behave as they do on the full dump.
"""

import hashlib

from ..jsonl import json_loads
from ..merge.pointers import get_header, root_form
from ..utils import remove_breves

MAX_PASSES = 5


def extract_sample(src, dst, language, lemmas=2000, include=()):
    include = set(include)
    keys = set()  # macronized headword keys of picked lemmas and their pointer chains
    lemma_count = 0
    for _, obj in _entries(src, language.code, json_loads):
        root = root_form(obj.get("senses", []), language)
        if root is None:
            lemma_count += 1
            if obj["word"] in include:
                keys.add(remove_breves(get_header(obj, language)))
        elif obj["word"] in include:
            keys.add(remove_breves(root))
    modulus = max(1, lemma_count // max(1, lemmas))

    picked = set()  # line numbers
    for _ in range(MAX_PASSES):
        added = False
        for line_no, obj in _entries(src, language.code, json_loads):
            if line_no in picked:
                continue
            key = remove_breves(get_header(obj, language))
            root = root_form(obj.get("senses", []), language)
            if root is None:
                # lemmas=0 keeps only the included words
                take = key in keys or (lemmas and _stable_hash(key) % modulus == 0)
            else:
                # A pointer comes along if it leads to a picked word or one leads to it
                root = remove_breves(root)
                take = root in keys or key in keys
                if take:
                    keys.add(root)
            if take:
                picked.add(line_no)
                keys.add(key)
                added = True
        if not added:
            break

    with open(src, encoding="utf-8") as f_in, open(dst, "w", encoding="utf-8") as f_out:
        for line_no, line in enumerate(f_in):
            if line_no in picked:
                f_out.write(line)
    return len(picked)


def _entries(src, lang_code, json_loads):
    with open(src, encoding="utf-8") as f:
        for line_no, line in enumerate(f):
            obj = json_loads(line)
            if obj.get("lang_code") == lang_code and "word" in obj:
                yield line_no, obj


def _stable_hash(text):
    return int.from_bytes(hashlib.md5(text.encode("utf-8")).digest()[:8], "big")
