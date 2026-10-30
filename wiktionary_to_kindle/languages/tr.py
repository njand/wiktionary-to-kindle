"""Turkish: the spellings a tap should find, and why a word in a Turkish text opens
nothing.

A Kindle folds case and accents in Latin letters, Turkish's among them: ı, İ, I and i weigh
the same, as do ş/s, ğ/g, ç/c, ö/o, ü/u and â/a, and an apostrophe weighs nothing. So a
form needs no case or accent variants. What a tap misses is morphology: Wiktionary's tables
list a noun's cases and possessives and a verb's tenses, but texts add the copula
(evdeydi), -ki, -le and derivations that no table lists (roadmap, Stage 12).
"""

import re

from . import Language
from .tr_forms import implied_forms
from .tr_suffixes import suffix_entries

# Suffixes left over when the longest stem the dictionary has is cut off a missed word,
# grouped by length: what a book split after that stem would leave for the reader
SUFFIX_LENGTHS = ((1, 2), (3, 4), (5, 99))
MIN_STEM = 3
APOSTROPHES = "'’"


def skips_form(form):
    """Whether a table form is no spelling a tap can reach: one with a space ("güzel
    miyim?", "gide gide"), since a long press selects one word, or with a character no
    word has ("Çerkez?ik"). Forms Kaikki could not tag are kept: they are the converbs
    (gidip, giderken) and an adjective's copula forms (güzeldim)."""
    return not all(char.isalpha() or char in "-" + APOSTROPHES for char in form["form"])


# A label inside the head line's parentheses, which render.headline cannot read:
# "(definite accusative kitabı, plural kitaplar or (obsolete) kütüp)"
INNER_LABEL = re.compile(r"\((obsolete|archaic|dialectal|colloquial|rare)\)\s*")


VOWELS = "aeıioöuüâîû"
# The vowel of a suffix with four forms (-ı, -i, -u, -ü), by the stem's last vowel
HARMONY = dict(zip(VOWELS, "ıiıiuüuüıiu"))
ACCUSATIVE = "definite accusative "
AORIST = "third-person singular simple present "


def head_line(text, pos, word):
    """The head line after the headword as Turkish dictionaries give it (TDK, Redhouse):
    a verb's aorist and a noun's accusative as the ending after what they share with the
    headword, the accusative only where it is not the regular one, and no plural, which
    is always regular. "(definite accusative kitabı, plural kitaplar)" → "(definite
    accusative -bı)"; "(definite accusative evi, plural evler)" → ""; "(third-person
    singular simple present gider)" → "(third-person singular simple present -der)"."""
    text = INNER_LABEL.sub(r"\1 ", text)
    match = re.search(r"\((.*)\)", text)
    if not match:
        return text
    kept = []
    for part in match.group(1).split(", "):
        if part.startswith(ACCUSATIVE):
            # Not "[please provide]", nor one cut short (esirlik, esirli)
            endings = [
                _ending(word, form, noun=True)
                for form in part[len(ACCUSATIVE) :].split(" or ")
                if not form.startswith("[")
                and form != _accusative(word)
                and not word.startswith(form)
            ]
            if endings:
                kept.append(ACCUSATIVE + " or ".join(endings))
        elif part.startswith(AORIST) and word.endswith(("mek", "mak")):
            forms = part[len(AORIST) :].split(" or ")
            kept.append(AORIST + " or ".join(_ending(word[:-3], f) for f in forms))
        elif not part.startswith("plural "):
            kept.append(part)
    rest = text[: match.start()] + text[match.end() :]
    return " ".join(
        filter(None, [rest.strip(), f"({', '.join(kept)})" if kept else ""])
    )


def _accusative(word):
    """The regular accusative: evi, kapıyı, saatı (saat's is saati, so it is shown)."""
    vowels = [char for char in word.lower() if char in VOWELS]
    if not vowels:
        return None
    return word + ("y" if word[-1] in VOWELS else "") + HARMONY[vowels[-1]]


def _ending(stem, form, noun=False):
    """form as the ending after what it shares with stem: gider after git is -der.
    A noun's ending starts at the consonant before it, as TDK writes it (burun, -rnu;
    hak, -kkı; saat, -ti), unless that is a vowel (kitap, -bı) or the ending follows an
    apostrophe (CD, -'yi)."""
    shared = 0
    while shared < min(len(stem), len(form)) and stem[shared] == form[shared]:
        shared += 1
    if not shared:
        return form
    if noun and form[shared - 1] not in VOWELS and form[shared] not in APOSTROPHES:
        shared -= 1
    return "-" + form[shared:]


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
    descendants=(),  # none: what Turkish gave other languages is no help to a reader
    homographs="<i>yüz</i>, face and hundred",
    miss_variants=miss_variants,
    extra_entries=suffix_entries,
)
