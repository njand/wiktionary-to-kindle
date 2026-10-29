import re
import shutil
import unicodedata
from importlib.resources import files
from itertools import product
from pathlib import Path

# Shipped inside the package so an installed wheel finds them
TEMPLATES = files("wiktionary_to_kindle") / "templates"

MACRON = "̄"
BREVE = "̆"


def normalize(text: str, lowercase: bool = False) -> str:
    """Normalize text by stripping diacritics and optionally converting to lowercase."""
    normalized = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    if lowercase:
        normalized = normalized.lower()
    return normalized


KINDLE_LIGATURES = {
    "ß": "ss",
    "æ": "ae",
    "Æ": "ae",
    "œ": "oe",
    "Œ": "oe",
    "ĳ": "ij",
    "Ĳ": "ij",
}


def kindle_fold(text: str) -> str:
    """Approximate the weights a Kindle compares a tapped word and an index label by.

    Per kindling's measurements: Latin letters weigh as their lowercase base letter (case and
    accents, macrons included, do not count), ß/æ/œ as ss/ae/oe, ASCII and general punctuation
    weigh nothing, and anything else, including a separate combining mark (the breve in ā̆),
    weighs as itself. Two strings with the same fold reach the same index labels.
    Approximation: Kindles fold only about half of Latin Extended-B; this folds all of it.
    """
    out = []
    for char in unicodedata.normalize("NFC", text):
        code = ord(char)
        if char in KINDLE_LIGATURES:
            out.append(KINDLE_LIGATURES[char])
        elif char.isascii():
            if char.isalnum() or char == " ":
                out.append(char.lower())
        elif _kindle_weighs_nothing(char, code):
            continue
        elif 0x00C0 <= code <= 0x024F and char.isalpha():
            base = unicodedata.normalize("NFKD", char)[0]
            out.append(base.lower() if base.isascii() else char)
        else:
            out.append(char)
    return "".join(out)


def _kindle_weighs_nothing(char, code):
    # Latin-1 punctuation and symbols, spacing modifiers, and general punctuation
    latin1_symbol = 0x00A1 <= code <= 0x00BF and char not in "µ¹²³"
    # Other symbols: kindling reaches "☿ōs" and "♃vis" (forms of ☿ and Iuppiter) from
    # "os" and "vis"; assumed for every symbol, not measured
    other_symbol = unicodedata.category(char) == "So"
    return (
        latin1_symbol
        or other_symbol
        or 0x02B0 <= code <= 0x02FF
        or 0x2000 <= code <= 0x206F
    )


def remove_breves(text: str) -> str:
    """Remove breve diacritics from characters in a given string."""
    normalized = unicodedata.normalize("NFD", text)
    filtered = "".join(c for c in normalized if c != BREVE)
    return unicodedata.normalize("NFC", filtered)


def generate_vowel_variants(word: str) -> list[str]:
    """Generate all possible variants of a Latin word with disputed vowel lengths resolved."""
    decomposed = unicodedata.normalize("NFD", word)

    # Group into (base_char, [combining_marks])
    groups = []
    for char in decomposed:
        if unicodedata.combining(char) == 0:
            groups.append((char, []))
        else:
            if groups:
                groups[-1][1].append(char)
            else:
                groups.append(("", [char]))

    options_per_group = []
    for base_char, marks in groups:
        has_macron = MACRON in marks
        has_breve = BREVE in marks

        if has_macron and has_breve:
            # Disputed vowel length: generate both short (unmacronized) and long (macronized) options
            remaining_marks = [m for m in marks if m not in (MACRON, BREVE)]
            short_str = unicodedata.normalize(
                "NFC", base_char + "".join(remaining_marks)
            )
            # NFC composes the vowel and macron into one character (ā)
            long_str = unicodedata.normalize(
                "NFC", base_char + MACRON + "".join(remaining_marks)
            )
            options_per_group.append([short_str, long_str])
        elif has_macron:
            remaining_marks = [m for m in marks if m != MACRON]
            macron_str = unicodedata.normalize(
                "NFC", base_char + MACRON + "".join(remaining_marks)
            )
            options_per_group.append([macron_str])
        else:
            normal_str = unicodedata.normalize("NFC", base_char + "".join(marks))
            options_per_group.append([normal_str])

    return ["".join(comb) for comb in product(*options_per_group)]


U_FOR_V = str.maketrans("vV", "uU")
J_FOR_I = str.maketrans("iI", "jJ")
VOWELS = set("aeiouyāēīōūȳAEIOUYĀĒĪŌŪȲ")
# Prefixes after which a root's initial i is consonantal: adiuvō, coniūnx, iniūria, obiectus
J_PREFIXES = ("ab", "ad", "con", "dis", "in", "inter", "ob", "per", "sub", "super")


def lookup_spellings(form: str) -> list[str]:
    """Every spelling of form a tap should find, the device folding only macrons and case.

    Disputed vowel lengths (ā̆) give both spellings. A combining mark that does not compose
    with its letter (the tie bar in Orphe͡us) weighs as itself, so the spelling without it is
    added. Wiktionary writes v for consonantal u and never j; texts that write u (uir) or j
    (jam, cujus) get a spelling each.
    """
    spellings = []
    for variant in generate_vowel_variants(form):
        for spelling in dict.fromkeys([variant, strip_marks(variant)]):
            spellings += [spelling, spelling.translate(U_FOR_V), j_for_i(spelling)]
    return list(dict.fromkeys(spellings))


# Separate combining marks that are abbreviation signs, not accents: a combining macron or
# overline on a consonant (n̄ for nōn) and the superscript letters scribes write (aͣ)
ABBREVIATION_MARKS = {"̄", "̅", *map(chr, range(0x0363, 0x0370))}


def strip_marks(text: str) -> str:
    """text without the accents that stay separate after NFC (the tie bar in Orphe͡us, the
    diaeresis in Boō̈tēs). Abbreviation signs are kept: without them it is another word."""
    composed = unicodedata.normalize("NFC", text)
    return "".join(
        c for c in composed if not unicodedata.combining(c) or c in ABBREVIATION_MARKS
    )


def j_for_i(word: str) -> str:
    """word with consonantal i written j: before a vowel at the start (iam), between vowels
    (cuius, maior), or at the start of a root after a prefix (adiuvō). An approximation;
    a wrong guess only adds a spelling no text uses."""
    word = unicodedata.normalize("NFC", word)
    # One base letter per character, so indexes match word's (a combining mark becomes "")
    lower = [normalize(char, lowercase=True) for char in word]
    chars = list(word)
    for i, char in enumerate(word):
        if char not in "iI" or i + 1 >= len(word):
            continue
        after = word[i + 1]
        if after not in VOWELS or lower[i + 1] == "i":
            continue
        if (
            i == 0
            or (
                word[i - 1] in VOWELS
                and "".join(lower[max(i - 2, 0) : i]) not in ("qu", "gu")
            )
            or "".join(lower[:i]) in J_PREFIXES
        ):
            chars[i] = char.translate(J_FOR_I)
    return "".join(chars)


# What follows the first lemma in a form_of target naming two: " and era", " m or f",
# " f and novāculum n", " n"
TWO_LEMMAS = re.compile(r" (?:[mfn] )?(?:and|or) | [mfn]$")


def form_of_root(sense: dict) -> str | None:
    """Return the lemma a sense merely points to, or None if the sense defines the word itself.

    "genitive singular of fors" or "alternative form of causa" only point at a lemma, while a
    participle sense like "loved; having been loved" (form_of amō) carries its own meaning.
    """
    targets = sense.get("alt_of") or sense.get("form_of")
    if targets:
        root = targets[0].get("word")
        glosses = normalize(" ".join(sense.get("glosses", [])), lowercase=True)
        # A form of root with no gloss at all (Kaikki tags it no-gloss) only points too
        if root and (
            normalize(root, lowercase=True) in glosses
            or (not glosses and "no-gloss" in sense.get("tags", []))
        ):
            # A form two lemmas share names both ("erus and era", "pār m or f"): take the
            # first linked word the target starts with. A phrase (ante diem) stays whole.
            if " " in root:
                links = [link[0] for link in sense.get("links", []) if link]
                root = next(
                    (
                        w
                        for w in links
                        if root.startswith(w + " ") and TWO_LEMMAS.match(root[len(w) :])
                    ),
                    root,
                )
            return root
        return None

    links = sense.get("links", [])
    if len(links) == 1 and len(links[0]) == 2 and links[0][1].endswith("#Latin"):
        root_word = links[0][0]
        for gloss in sense.get("glosses", []):
            if gloss.endswith(f" of {root_word}"):
                return root_word
    return None


def sanitize_xhtml(text: str) -> str:
    """Escapes stray `&` and `<` characters that break XML parsing."""
    if not text:
        return text
    # Escapes `&` unless it starts a character reference or one of XML's five entities
    text = re.sub(
        r"&(?!(?:#[0-9]+|#x[0-9a-fA-F]+|amp|lt|gt|quot|apos);)", "&amp;", text
    )
    # Escapes `<` if it does not start a valid standard XHTML tag
    return re.sub(
        r"<(?!(?:/?(?:br|b|i|span|a|p|sup|sub|small|strong|em|div|ul|ol|li|hr|idx:[a-z]+)\b))",
        "&lt;",
        text,
        flags=re.IGNORECASE,
    )


def find_kindling() -> Path | None:
    """Locate kindling on PATH, under the name its releases or a package manager give it."""
    for name in ("kindling-cli", "kindling"):
        if found := shutil.which(name):
            return Path(found)
    return None
