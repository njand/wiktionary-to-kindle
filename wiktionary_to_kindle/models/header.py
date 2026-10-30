import re
import unicodedata

from ..utils import normalize, sanitize_xhtml

_ABBREVIATION_PATTERN = re.compile(
    r"\b(present infinitive|perfect active|supine|genitive|feminine|neuter)\b\s*"
)


def find_unaccented(text, word):
    """Return the (start, end) span of text that reads as word once accents are stripped,
    including the combining marks after its last letter (the breve of ā̆), or None."""
    if not word:
        return None
    # offsets[k] is the index in text of the k-th character of the accent-stripped text
    offsets = []
    for i, char in enumerate(text):
        offsets.extend([i] * len(normalize(char)))
    start = "".join(normalize(char) for char in text).find(word)
    if start == -1:
        return None
    end = offsets[start + len(word) - 1] + 1
    while end < len(text) and unicodedata.combining(text[end]):
        end += 1
    return offsets[start], end


class Header:
    def __init__(self, plain_word, full_header_text, num_headers=0):
        self.plain_word = plain_word
        self.full_header_text = full_header_text
        self.num_headers = num_headers

        self.head_word = None
        self.prefix = None
        self.remainder = None
        self.labelled = (
            None  # the remainder with its labels ("genitive rēgis"), as markup
        )

        self.split_components()

    def split_components(self):
        span = find_unaccented(self.full_header_text, self.plain_word)

        if span is None:  # word not found in expansion
            self.head_word = self.plain_word
            self.prefix = ""
            self.remainder = self.full_header_text
        else:
            start_idx, end_idx = span
            self.head_word = self.full_header_text[start_idx:end_idx].strip()
            self.prefix = self.full_header_text[:start_idx]
            self.remainder = self.full_header_text[end_idx:].strip()
            self.labelled = sanitize_xhtml(self.remainder)
            self.abbreviate_grammatical_forms()

        # The prefix is escaped by the templates; the remainder is inserted as markup
        self.remainder = sanitize_xhtml(self.remainder)

    def abbreviate_grammatical_forms(self):
        cleaned = _ABBREVIATION_PATTERN.sub("", self.remainder)
        self.remainder = re.sub(r"\s{2,}", " ", cleaned).strip()
