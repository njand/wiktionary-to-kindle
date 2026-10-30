import re
import shutil
import unicodedata
from importlib.resources import files
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

    text is weighed as written, not normalized: a decomposed ā (a and a combining macron)
    or a Greek oxia (U+1F71, which NFC turns into tonos) weighs differently on the device.
    """
    out = []
    for char in text:
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


VOWELS = set("aeiouyāēīōūȳAEIOUYĀĒĪŌŪȲ")

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


# What follows the first lemma in a form_of target naming two: " and era", " m or f",
# " f and novāculum n", " n"
TWO_LEMMAS = re.compile(r" (?:[mfn] )?(?:and|or) | [mfn]$")


def form_of_root(sense: dict, language) -> str | None:
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
    if len(links) == 1 and len(links[0]) == 2 and links[0][1].endswith(language.anchor):
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
