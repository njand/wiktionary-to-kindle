import re
from ..utils import normalize, BREVE

_ABBREVIATION_PATTERN = re.compile(
    r"\b(present infinitive|perfect active|supine|genitive|feminine|neuter)\b\s*"
)

class Header:
    def __init__(self, plain_word, full_header_text, num_headers=0):
        self.plain_word = plain_word
        self.full_header_text = full_header_text
        self.num_headers = num_headers
        
        self.head_word = None
        self.prefix = None
        self.remainder = None
        
        self.split_components()
    
    def split_components(self):
        unmacronized_text = normalize(self.full_header_text)
        
        start_idx = unmacronized_text.find(self.plain_word)
        end_idx = start_idx + len(self.plain_word)
        
        if start_idx == -1:  # word not found in expansion
            self.head_word = self.plain_word
            self.prefix = ''
            self.remainder = self.full_header_text
        else:
            last_end_idx = end_idx
            breve_count = 1
            while breve_count > 0:
                self.head_word = self.full_header_text[start_idx:end_idx]
                new_end_idx = end_idx + self.head_word.count(BREVE)
                breve_count = self.full_header_text[last_end_idx:new_end_idx].count(BREVE)
                if new_end_idx < len(self.full_header_text) and self.full_header_text[new_end_idx] == BREVE:
                    new_end_idx += 1
                last_end_idx = new_end_idx

            self.head_word = self.full_header_text[start_idx:last_end_idx].strip()
            self.prefix = self.full_header_text[:start_idx]
            self.remainder = self.full_header_text[last_end_idx:].strip()
            self.abbreviate_grammatical_forms()
    
    def abbreviate_grammatical_forms(self):
        cleaned = _ABBREVIATION_PATTERN.sub("", self.remainder)
        self.remainder = re.sub(r"\s{2,}", " ", cleaned).strip()