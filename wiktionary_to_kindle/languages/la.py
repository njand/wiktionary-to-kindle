"""Latin: the spellings a tap should find, the forms Wiktionary implies, and why a word in a
Latin text opens nothing."""

import re
import unicodedata
from itertools import product

from ..utils import BREVE, MACRON, VOWELS, normalize, strip_marks
from . import Language
from .la_forms import implied_forms


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


ENCLITICS = ("que", "ne", "ve")
CONSONANTAL_U = re.compile(r"[uU](?=[aeiouāēīōūAEIOU])")


def miss_variants(word):
    """(causes, variant) for the spellings a Latin text has but Wiktionary's headwords do
    not: an enclitic, j for consonantal i, u for consonantal v."""
    bases = [((), word)]
    for enclitic in ENCLITICS:
        if word.lower().endswith(enclitic) and len(word) > len(enclitic) + 1:
            bases.append(((f"enclitic -{enclitic}",), word[: -len(enclitic)]))

    for causes, base in bases:
        spellings = [(causes, base)]
        if "j" in base.lower():
            spellings.append(
                (causes + ("j for i",), base.replace("j", "i").replace("J", "I"))
            )
        if CONSONANTAL_U.search(base):
            spellings += [
                (
                    c + ("u for v",),
                    CONSONANTAL_U.sub(lambda m: "vV"[m.group().isupper()], w),
                )
                for c, w in list(spellings)
            ]
        for variant in spellings:
            if variant[0]:
                yield variant


LATIN = Language(
    code="la",
    name="Latin",
    index_name="Latin",
    lookup_spellings=lookup_spellings,
    # Page titles have no macrons (iuro for iūrō), and some targets other ones (acontīzō)
    letters=normalize,
    alternative_tags=frozenset({"alternative", "Medieval-Latin"}),
    periphrastic=r".* (sum|esse|fuisse|fore|erat|erit|est|sit|esset|iri|īrī)",
    pos_by_head_template={"la-part": "participle", "la-gerund": "gerund"},
    implied_forms=implied_forms,
    descendants=("English", "Portuguese", "Spanish", "French", "Italian"),
    homographs="<i>latus</i>, <i>lātus</i>",
    miss_variants=miss_variants,
)
