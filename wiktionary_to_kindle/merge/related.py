"""What a page merged into its lemma during merge_dump says beyond its forms.

A page that only points to a lemma becomes part of it, so a tap on frīgidulus opens frīgidus.
When the page is a word of its own (a diminutive, a comparative, an alternative spelling),
the lemma keeps a line for it, with the page's own meaning when it has one:
"dim. frīgidulus: somewhat cold". Inflections (genitive singular of fors) and participles
get no line; they are forms of the lemma, and its forms are not listed.
"""

import re

from ..utils import normalize

MERGED_KEY = "merged_pages"  # where merge_dump keeps them on the lemma's JSON

# The start of a pointer gloss ("diminutive of ..."), and the label its line gets
KINDS = [
    (r"diminutive", "dim."),
    (r"comparative degree", "comp."),
    (r"superlative degree", "superl."),
    (r"female equivalent", "fem."),
    (r"alternative (?:form|spelling|typography)", "alt."),
    (r"(?:archaic|old) latin form|archaic form", "archaic"),
    (r"medieval (?:latin form|spelling)", "medieval"),
    (r"abbreviation|initialism|contraction|praenominal abbreviation", "abbr."),
    (r"synonym", "syn."),
]
KIND_PATTERN = re.compile(
    r"^(?:" + "|".join(f"(?P<k{i}>{p})" for i, (p, _) in enumerate(KINDS)) + r") of\s+",
    re.IGNORECASE,
)
# The root's own gloss, which Wiktionary repeats after it: diminutive of flūctus (“wave”)
ROOT_GLOSS = re.compile(r"^\s*\((?:“[^”]*”|\"[^\"]*\")[^)]*\)")


def merged_page(json_entry, header):
    """{"kind", "word", "gloss"} for a pointer page that is a word of its own, else None.
    header is the page's macronized headword."""
    for sense in json_entry.get("senses", []):
        gloss = " ".join(sense.get("glosses", []))
        match = KIND_PATTERN.match(gloss)
        if not match:
            continue
        targets = sense.get("alt_of") or sense.get("form_of") or [{}]
        rest = _after_root(gloss[match.end() :], targets[0].get("word", ""))
        # Leftovers of the pointer (esed: "/ esset / estō", s. v.: "s.v") are no meaning
        if not rest[:1].isalpha() or _letters(rest) == _letters(header):
            rest = ""
        kind = next(label for i, (_p, label) in enumerate(KINDS) if match[f"k{i}"])
        return {"kind": kind, "word": header, "gloss": rest}
    return None


def _letters(text):
    return "".join(char for char in normalize(text, lowercase=True) if char.isalpha())


def _after_root(text, root):
    """text with the root word and the root's own gloss removed: what the page adds. When
    the text does not start with the root, only what follows a colon or semicolon."""
    plain = normalize(text, lowercase=True)
    root_plain = normalize(root, lowercase=True)
    if not root_plain or not plain.startswith(root_plain):
        separator = min((text.find(c) for c in ":;" if c in text), default=-1)
        return text[separator + 1 :].strip() if separator != -1 else ""
    # normalize drops combining marks, so step over the root in text letter by letter
    i, seen = 0, 0
    while i < len(text) and seen < len(root_plain):
        seen += len(normalize(text[i]))
        i += 1
    while i < len(text) and not normalize(text[i]):
        i += 1
    text = ROOT_GLOSS.sub("", text[i:])
    return text.strip(" :;,.-–—").strip()


def related_lines(merged, header_text):
    """Group merged pages by kind for rendering: [(kind, [(word, gloss), ...])], in the
    order of KINDS. A comparative or superlative the header already names (lātus: comparative
    lātior) and that adds no meaning is left out."""
    shown = normalize(header_text or "", lowercase=True)
    by_kind = {}
    for page in merged:
        word, gloss = page["word"], page["gloss"]
        if (
            page["kind"] in ("comp.", "superl.")
            and not gloss
            and re.search(rf"\b{re.escape(normalize(word, lowercase=True))}\b", shown)
        ):
            continue
        words = by_kind.setdefault(page["kind"], {})
        if gloss and not words.get(word):
            words[word] = gloss
        else:
            words.setdefault(word, gloss)
    order = [label for _p, label in KINDS]
    return [
        (kind, list(by_kind[kind].items())) for kind in sorted(by_kind, key=order.index)
    ]
