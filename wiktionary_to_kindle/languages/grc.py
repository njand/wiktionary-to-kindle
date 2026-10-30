"""Ancient Greek. Only what the shared pipeline needs to build it; the spellings a Greek
text prints come with Stage 9 of the roadmap.

A Kindle folds no Greek letter: case and accents count, so a label without accents would
reach nothing. Length marks (ᾱ, ῠ) are another matter: Wiktionary's headwords and table
forms carry them, its page titles and the texts readers tap do not.
"""

import unicodedata

from ..utils import BREVE, MACRON
from . import Language


def strip_length(text: str) -> str:
    """text without macrons and breves, keeping accents and breathings: λῡ̆́ω → λύω."""
    decomposed = unicodedata.normalize("NFD", text)
    kept = "".join(c for c in decomposed if c not in (MACRON, BREVE))
    return unicodedata.normalize("NFC", kept)


def lookup_spellings(form: str) -> list[str]:
    """The form as Wiktionary spells it, for now (roadmap, Stage 9)."""
    return [form]


def implied_forms(forms, known):
    return []


def miss_variants(word):
    return []


ANCIENT_GREEK = Language(
    code="grc",
    name="Ancient Greek",
    index_name="Greek",
    lookup_spellings=lookup_spellings,
    # Accents and breathings belong to the spelling (ὅς, ὡς and ὥς are three words)
    letters=strip_length,
    alternative_tags=frozenset({"alternative"}),
    periphrastic=None,
    pos_by_head_template={},
    implied_forms=implied_forms,
    # To be chosen with a sample (roadmap, Stage 10)
    descendants=("Latin", "English"),
    homographs="<i>εἶ</i>, of <i>εἰμί</i> and of <i>εἶμι</i>",
    miss_variants=miss_variants,
)
