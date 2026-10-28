"""Forms added to an entry during merge_dump, from what its own forms already say.

Wiktionary lists a verb's participles and an adjective's comparative and superlative only in
the nominative; their declension is on the participle's or comparative's own page, which many
lack. For those, the regular declension is generated and added to the entry, each form tagged
"generated". A form whose page exists is left alone: that page is merged in (or is an entry
of its own), and a second copy of its labels would only list both in the popup.

Alternative spellings (inlābor beside illābor) are kept as labels, except those with a page
of their own, for the same reason, and reconstructions (*luttra), which no text spells.
"""

import unicodedata

from ..utils import normalize, remove_breves

GENERATED = "generated"
ALTERNATIVE_TAGS = {"alternative", "Medieval-Latin"}

M, F, N = "masculine", "feminine", "neuter"
NOM, GEN, DAT, ACC, ABL, VOC = (
    "nominative",
    "genitive",
    "dative",
    "accusative",
    "ablative",
    "vocative",
)
SG, PL = "singular", "plural"

# Endings after the stem, with the tags Kaikki gives the same cells; the nominative is
# left out, the entry already has it
FIRST_SECOND = [
    ("ī", [M, N, GEN, SG]),
    ("ō", [M, N, DAT, ABL, SG]),
    ("um", [M, ACC, SG]),
    ("e", [M, VOC, SG]),
    ("a", [F, NOM, VOC, SG]),
    ("ae", [F, GEN, DAT, SG]),
    ("am", [F, ACC, SG]),
    ("ā", [F, ABL, SG]),
    ("um", [N, NOM, ACC, VOC, SG]),
    ("ī", [M, NOM, VOC, PL]),
    ("ae", [F, NOM, VOC, PL]),
    ("a", [N, NOM, ACC, VOC, PL]),
    ("ōrum", [M, N, GEN, PL]),
    ("ārum", [F, GEN, PL]),
    ("īs", [M, F, N, DAT, ABL, PL]),
    ("ōs", [M, ACC, PL]),
    ("ās", [F, ACC, PL]),
]
PRESENT_PARTICIPLE = [  # after amant-
    ("is", [M, F, N, GEN, SG]),
    ("ī", [M, F, N, DAT, ABL, SG]),
    ("em", [M, F, ACC, SG]),
    ("e", [M, F, N, ABL, SG]),
    ("ēs", [M, F, NOM, ACC, VOC, PL]),
    ("īs", [M, F, ACC, PL]),
    ("ia", [N, NOM, ACC, VOC, PL]),
    ("ium", [M, F, N, GEN, PL]),
    ("ibus", [M, F, N, DAT, ABL, PL]),
]
COMPARATIVE = [  # after lāt-
    ("ius", [N, NOM, ACC, VOC, SG]),
    ("iōris", [M, F, N, GEN, SG]),
    ("iōrī", [M, F, N, DAT, SG]),
    ("iōrem", [M, F, ACC, SG]),
    ("iōre", [M, F, N, ABL, SG]),
    ("iōrēs", [M, F, NOM, ACC, VOC, PL]),
    ("iōra", [N, NOM, ACC, VOC, PL]),
    ("iōrum", [M, F, N, GEN, PL]),
    ("iōribus", [M, F, N, DAT, ABL, PL]),
]
SHORTEN = str.maketrans("āēīōū", "aeiou")
CASES = {NOM, GEN, DAT, ACC, ABL, VOC}
TENSES = {"present", "perfect", "future"}


def enrich_forms(forms, known, merged=()):
    """Return an entry's own forms, less alternative spellings that have a page (known holds
    the dump's headwords without breves), then the forms merged from pages that point to it,
    then the declensions these imply."""
    forms = [form for form in forms if not _redundant_alternative(form, known)]
    forms += merged
    implied = [pair for form in forms for pair in decline(form, known)]
    implied += superlative_adverb(forms, known)

    have = {form.get("form") for form in forms}
    generated = []
    for spelling, tags in implied:
        if spelling not in have:
            have.add(spelling)
            generated.append({"form": spelling, "tags": [*tags, GENERATED]})
    return forms + generated


def decline(form, known):
    """(spelling, tags) of the declension a nominative form implies, or none when it has a
    page of its own or is not a regular participle, comparative or superlative."""
    word, tags = form.get("form", ""), set(form.get("tags", []))
    if not _is_word(word) or remove_breves(word) in known:
        return []
    plain = normalize(remove_breves(word), lowercase=True)

    if "participle" in tags and tags & TENSES and not tags & (CASES | {"form-of"}):
        own = sorted(tags)
        if "present" in tags and plain.endswith("ns"):
            # The vowel is long before ns, short before nt: amāns, amantis
            stem = word[:-3] + word[-3].translate(SHORTEN) + "nt"
            return _apply(stem, PRESENT_PARTICIPLE, own)
        if plain.endswith("us"):
            return _apply(word[:-2], FIRST_SECOND, own)
        return []

    if tags == {"comparative"} and plain.endswith("ior"):
        return _apply(word[:-3], COMPARATIVE, ["comparative"])
    if tags == {"superlative"} and plain.endswith("mus"):
        return _apply(word[:-2], FIRST_SECOND, ["superlative"])
    return []


def superlative_adverb(forms, known):
    """The adverb lātissimē, when the entry tags an adverb (lātē) and a superlative but the
    adverb has no page, whose own superlative it would be."""
    tagged = {}
    for form in forms:
        if len(form.get("tags", [])) == 1:
            tagged.setdefault(form["tags"][0], form.get("form", ""))
    adverb, superlative = tagged.get("adverb"), tagged.get("superlative")
    if not adverb or not superlative or remove_breves(adverb) in known:
        return []
    if not _is_word(superlative) or not normalize(superlative).endswith("mus"):
        return []
    return [(superlative[:-2] + "ē", ["adverb", "superlative"])]


def _apply(stem, table, own_tags):
    return [(stem + ending, own_tags + tags) for ending, tags in table]


def _is_word(word):
    """A single Latin word: letters and combining marks only (no spaces, hyphens, *)."""
    return bool(word) and all(
        char.isalpha() or unicodedata.combining(char) for char in word
    )


def _redundant_alternative(form, known):
    tags = set(form.get("tags", []))
    if not tags & ALTERNATIVE_TAGS:
        return False
    word = form.get("form", "")
    return (
        "reconstruction" in tags or word.startswith("*") or remove_breves(word) in known
    )
