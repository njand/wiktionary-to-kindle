import os
import re
import shutil
import sys
import unicodedata
from itertools import product
from pathlib import Path

MACRON = "̄"
BREVE = "̆"
MACRONIZED_VOWELS = {
    "a": "ā",
    "A": "Ā",
    "e": "ē",
    "E": "Ē",
    "i": "ī",
    "I": "Ī",
    "o": "ō",
    "O": "Ō",
    "u": "ū",
    "U": "Ū",
    "y": "ȳ",
    "Y": "Ȳ",
}


def normalize(text: str, lowercase: bool = False) -> str:
    """Normalize text by stripping diacritics and optionally converting to lowercase."""
    normalized = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    if lowercase:
        normalized = normalized.lower()
    return normalized


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

            if base_char in MACRONIZED_VOWELS and not remaining_marks:
                long_str = MACRONIZED_VOWELS[base_char]
            else:
                long_str = unicodedata.normalize(
                    "NFC", base_char + MACRON + "".join(remaining_marks)
                )

            options_per_group.append([short_str, long_str])
        elif has_macron:
            remaining_marks = [m for m in marks if m != MACRON]
            if base_char in MACRONIZED_VOWELS and not remaining_marks:
                macron_str = MACRONIZED_VOWELS[base_char]
            else:
                macron_str = unicodedata.normalize(
                    "NFC", base_char + MACRON + "".join(remaining_marks)
                )
            options_per_group.append([macron_str])
        else:
            normal_str = unicodedata.normalize("NFC", base_char + "".join(marks))
            options_per_group.append([normal_str])

    return ["".join(comb) for comb in product(*options_per_group)]


def form_of_root(sense: dict) -> str | None:
    """Return the lemma a sense merely points to, or None if the sense defines the word itself.

    "genitive singular of fors" or "alternative form of causa" only point at a lemma, while a
    participle sense like "loved; having been loved" (form_of amō) carries its own meaning.
    """
    targets = sense.get("alt_of") or sense.get("form_of")
    if targets:
        root = targets[0].get("word")
        glosses = normalize(" ".join(sense.get("glosses", [])), lowercase=True)
        if root and normalize(root, lowercase=True) in glosses:
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
    """Escapes stray `<` characters that break KindleGen XML parsing."""
    if not text:
        return text
    # Escapes `<` if it does not start a valid standard XHTML tag
    return re.sub(
        r"<(?!(?:/?(?:br|b|i|span|a|p|sup|sub|small|strong|em|div|ul|ol|li|hr|idx:[a-z]+)\b))",
        "&lt;",
        text,
        flags=re.IGNORECASE,
    )


def find_kindlegen() -> Path | None:
    """Locates the kindlegen binary via PATH or common installation directories."""
    # 1. Check system PATH first
    binary_name = "kindlegen.exe" if sys.platform == "win32" else "kindlegen"
    found_in_path = shutil.which(binary_name)
    if found_in_path:
        return Path(found_in_path)

    # 2. Check explicit installation directories if not in PATH
    possible_paths = []

    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("PROGRAMFILES", "")
        prog_files_x86 = os.environ.get("PROGRAMFILES(X86)", "")

        for base in (local_app, prog_files, prog_files_x86):
            if base:
                possible_paths.append(
                    Path(base)
                    / "Amazon"
                    / "Kindle Previewer 3"
                    / "lib"
                    / "fc"
                    / "bin"
                    / "kindlegen.exe"
                )
    elif sys.platform == "darwin":
        possible_paths.append(
            Path(
                "/Applications/Kindle Previewer 3.app/Contents/MacOS/lib/fc/bin/kindlegen"
            )
        )
    else:  # Linux / Unix
        possible_paths.extend(
            [
                Path("/usr/local/bin/kindlegen"),
                Path("/usr/bin/kindlegen"),
                Path("/opt/kindlegen/kindlegen"),
                Path.home() / ".local" / "bin" / "kindlegen",
            ]
        )

    for path in possible_paths:
        if path.is_file() and os.access(path, os.X_OK):
            return path

    return None
