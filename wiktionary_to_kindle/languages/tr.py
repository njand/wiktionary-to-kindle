"""Turkish: the spellings a tap should find, and why a word in a Turkish text opens
nothing.

A Kindle folds case and accents in Latin letters, Turkish's among them: ı, İ, I and i weigh
the same, as do ş/s, ğ/g, ç/c, ö/o, ü/u and â/a, and an apostrophe weighs nothing. So a
form needs no case or accent variants. What a tap misses is morphology: Wiktionary's tables
list a noun's cases and possessives and a verb's tenses, but texts add the copula
(evdeydi), -ki, -le and derivations that no table lists (roadmap, Stage 12).
"""

from . import Language

# Suffixes left over when the longest stem the dictionary has is cut off a missed word,
# grouped by length: what a book split after that stem would leave for the reader
SUFFIX_LENGTHS = ((1, 2), (3, 4), (5, 99))
MIN_STEM = 3
APOSTROPHES = "'’"


def skips_form(form):
    """Whether a table form is no spelling a tap can reach: one with a space ("güzel
    miyim?", "gide gide"), since a long press selects one word."""
    return " " in form.get("form", "")


def head_line(text, pos):
    """The head line after the headword: "(definite accusative evi, plural evler)"."""
    return text


def implied_forms(forms, known):
    return []


def miss_variants(word):
    """(causes, variant) for a Turkish word that opens nothing: a proper noun with its
    suffixes after an apostrophe (Türkiye'nin), then the longest stem the dictionary has,
    named by how many letters of suffixes are left after it (evdeydi: ev + 5 letters).
    A stem must keep MIN_STEM letters, so a short word that misses stays unknown."""
    for mark in APOSTROPHES:
        if mark in word:
            yield ("apostrophe",), word.split(mark)[0]
    letters = word.translate({ord(mark): None for mark in APOSTROPHES})
    for end in range(len(letters) - 1, MIN_STEM - 1, -1):
        left = len(letters) - end
        low, high = next((lo, hi) for lo, hi in SUFFIX_LENGTHS if lo <= left <= hi)
        name = f"stem + {low}–{high} letters" if high < 99 else f"stem + {low}+ letters"
        yield (name,), letters[:end]


TURKISH = Language(
    code="tr",
    name="Turkish",
    index_name="Turkish",
    # The page title: what form-of links name. Head lines spell it the same
    headword=lambda header: header.plain_word,
    lookup_spellings=lambda form: [form],
    # The device folds case in Latin letters, ı and İ included
    capitalizes=lambda pos, headword: False,
    # Circumflexes are not always written (kâğıt, kağıt); the rest are letters of their own
    letters=lambda text: text.translate(str.maketrans("âîûÂÎÛ", "aiuAIU")),
    alternative_tags=frozenset({"alternative"}),
    skips_form=skips_form,
    pos_by_head_template={},
    implied_forms=implied_forms,
    head_line=head_line,
    genders={},
    descendants=(),
    homographs="<i>yüz</i>, face and hundred",
    miss_variants=miss_variants,
)
