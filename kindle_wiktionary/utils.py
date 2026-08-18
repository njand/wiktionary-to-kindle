import unicodedata
from itertools import product


MACRON = '̄'
BREVE = '̆'
MACRONIZED_VOWELS = {
    "a": "ā", "A": "Ā",
    "e": "ē", "E": "Ē",
    "i": "ī", "I": "Ī",
    "o": "ō", "O": "Ō",
    "u": "ū", "U": "Ū",
    "y": "ȳ", "Y": "Ȳ"
}


def normalize(text: str, lowercase: bool = False) -> str:
    """Normalize text by stripping diacritics and optionally converting to lowercase."""
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    if lowercase:
        normalized = normalized.lower()
    return normalized


def remove_breves(text: str) -> str:
    """Remove breve diacritics from characters in a given string."""
    normalized = unicodedata.normalize("NFD", text)
    filtered = ''.join(c for c in normalized if c != BREVE)
    return unicodedata.normalize("NFC", filtered)


def generate_vowel_variants(word: str) -> list:
    """Generate all possible variants of a Latin word with only disputed vowel lengths changed."""
    decomposed = unicodedata.normalize("NFD", word)
    disputed_vowel_positions = []
    base_word_chars = []
    i = 0
    
    while i < len(decomposed):
        char = decomposed[i]
        base_word_chars.append(char)
        if i + 1 < len(decomposed) and decomposed[i+1] == MACRON:
            if i + 2 < len(decomposed) and decomposed[i+2] == BREVE:  # Check for disputed length marks
                disputed_vowel_positions.append(len(base_word_chars) - 1)
                i += 2
            else:
                base_word_chars[-1] = MACRONIZED_VOWELS.get(char, char)
                i += 1    
        i += 1
    
    base_word = unicodedata.normalize("NFC", "".join(base_word_chars))
    
    if not disputed_vowel_positions:
        return [base_word]
    
    variants = []
    for combination in product(*[(base_word[pos], MACRONIZED_VOWELS[base_word[pos]]) for pos in disputed_vowel_positions]):
        new_word = list(base_word)
        for pos, replacement in zip(disputed_vowel_positions, combination):
            new_word[pos] = replacement
        variants.append("".join(new_word))
    
    return variants
