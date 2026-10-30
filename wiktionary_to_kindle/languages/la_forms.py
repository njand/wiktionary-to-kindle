"""The regular forms Latin entries imply, generated during merge_dump (merge.forms).

Wiktionary lists a verb's participles and an adjective's comparative and superlative only in
the nominative; their declension is on the participle's or comparative's own page, which many
lack. For those, the regular declension is generated.
"""

import unicodedata

from ..utils import normalize, remove_breves

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
FEMININE = [
    (ending, [c for c in tags if c != F]) for ending, tags in FIRST_SECOND if F in tags
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


def implied_forms(forms, known, entry=None):
    """(spelling, tags) of the declensions an entry's forms imply, and its superlative
    adverb. known holds the dump's headwords without breves."""
    implied = [pair for form in forms for pair in decline(form, known)]
    return implied + superlative_adverb(forms, known)


def decline(form, known):
    """(spelling, tags) of the declension a nominative form implies, or none when it has a
    page of its own or is not a regular participle, comparative or superlative."""
    word, tags = form.get("form", ""), set(form.get("tags", []))
    if not is_word(word) or remove_breves(word) in known:
        return []
    plain = normalize(remove_breves(word), lowercase=True)

    if "participle" in tags and tags & TENSES and not tags & (CASES | {"form-of"}):
        own = sorted(tags)
        if "present" in tags and plain.endswith("ns"):
            # The vowel is long before ns, short before nt: amāns, amantis
            stem = word[:-3] + word[-3].translate(SHORTEN) + "nt"
            return apply(stem, PRESENT_PARTICIPLE, own)
        if plain.endswith("us"):
            return apply(word[:-2], FIRST_SECOND, own)
        return []

    if tags == {"comparative"} and plain.endswith("ior"):
        return apply(word[:-3], COMPARATIVE, ["comparative"])
    if tags == {"superlative"} and plain.endswith("mus"):
        return apply(word[:-2], FIRST_SECOND, ["superlative"])
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
    if not is_word(superlative) or not normalize(superlative).endswith("mus"):
        return []
    return [(superlative[:-2] + "ē", ["adverb", "superlative"])]


def greek_accusatives(forms, entry):
    """(spelling, tags) of the Latin and Greek accusatives beside the ones a Greek noun's
    table gives: Ācin → Ācim, Philoctētēn → Philoctētem, Typhōea → Typhōeum, and for a
    third-declension noun from Greek iaspidem → iaspida, cyclōpēs → cyclōpas."""
    if entry.get("pos") not in ("noun", "name"):
        return []
    head = normalize(head_word(entry))
    greek_third = _from_greek(entry) and any(
        "declension-3" in sense.get("tags", []) for sense in entry.get("senses", [])
    )
    implied = []
    for form in forms:
        word, tags = form.get("form", ""), form.get("tags", [])
        if ACC not in tags or not is_word(word):
            continue
        if SG in tags:
            if word.endswith("in"):
                implied.append((word[:-1] + "m", tags))
            elif word.endswith("ēn"):
                implied.append((word[:-2] + "em", tags))
            elif word.endswith("ea") and head.endswith("eus"):
                implied.append((word[:-1] + "um", tags))
            elif word.endswith("em") and greek_third:
                implied.append((word[:-2] + "a", tags))
        elif PL in tags and word.endswith("ēs") and greek_third:
            implied.append((word[:-2] + "as", tags))
    return implied


# Etymology templates that name a word's source (borrowed, derived, inherited)
FROM_TEMPLATES = {"bor", "bor+", "lbor", "slbor", "der", "der+", "inh", "inh+", "uder"}
# A name's declension by its ending, when Wiktionary gives no table (Anaximander)
NAME_SINGULAR = {
    "us": [
        ("ī", [GEN, SG]),
        ("ō", [DAT, ABL, SG]),
        ("um", [ACC, SG]),
        ("e", [VOC, SG]),
    ],
    "er": [("ī", [GEN, SG]), ("ō", [DAT, ABL, SG]), ("um", [ACC, SG])],  # after -r
    "a": [("ae", [GEN, DAT, SG]), ("am", [ACC, SG]), ("ā", [ABL, SG])],
    "um": [("ī", [GEN, SG]), ("ō", [DAT, ABL, SG])],
    "ēs": [("em", [ACC, SG]), ("ēn", [ACC, SG])],
}
# The plural of a second-declension name with only a singular table: Lȳdus, Lȳdī
NAME_PLURAL = [
    ("ī", [NOM, VOC, PL]),
    ("ōrum", [GEN, PL]),
    ("īs", [DAT, ABL, PL]),
    ("ōs", [ACC, PL]),
]


def name_forms(forms, entry):
    """(spelling, tags) of a name's declension: its singular when Wiktionary gives no
    accusative (Anaximander, or Philoctētēs with a genitive only), the plural when it gives
    a second-declension singular only."""
    if entry.get("pos") != "name":
        return []
    head = head_word(entry)
    if not is_word(head):
        return []
    cases = [form for form in forms if set(form.get("tags", [])) & CASES]
    if not any(ACC in form.get("tags", []) for form in cases):
        for ending, table in NAME_SINGULAR.items():
            if head.endswith(ending):
                stem = head[:-2] + "r" if ending == "er" else head[: -len(ending)]
                return apply(stem, table, [])
        return []
    if head.endswith("us") and not any(PL in form.get("tags", []) for form in cases):
        return apply(head[:-2], NAME_PLURAL, [])
    return []


def feminine_forms(forms, known, entry):
    """(spelling, tags) of the first declension of a noun's feminine (catulus, catula →
    catulae), when it has no page of its own."""
    if entry.get("pos") != "noun":
        return []
    return [
        pair
        for form in forms
        if form.get("tags") == [F]
        and form.get("form", "").endswith("a")
        and is_word(form["form"])
        and remove_breves(form["form"]) not in known
        for pair in apply(form["form"][:-1], FEMININE, [F])
    ]


def genitives_in_um(forms):
    """(spelling, tags) of the genitive plural in -um beside -ium of a participle or
    adjective in -ns (prūdentum, rēgnantum), poetic and late."""
    return [
        (form["form"][:-3] + "um", form["tags"])
        for form in forms
        if form.get("form", "").endswith("ntium")
        and {GEN, PL} <= set(form.get("tags", []))
    ]


def head_word(entry):
    """An entry's headword as its head line spells it (Cēphīsus), without breves."""
    head_templates = entry.get("head_templates") or [{}]
    expansion = head_templates[0].get("expansion", "") or entry.get("word", "")
    return remove_breves(expansion.split(" ")[0]) if expansion else ""


def _from_greek(entry):
    """Whether an entry's etymology says it comes from Ancient Greek: {{bor|la|grc}},
    {{der|la|grc}} or {{ety|la|:bor|grc:...}}, not a Greek cognate."""
    for template in entry.get("etymology_templates", []):
        args = template.get("args", {})
        if template.get("name") in FROM_TEMPLATES and args.get("2") == "grc":
            return True
        if template.get("name") == "ety" and str(args.get("3", "")).startswith("grc:"):
            return True
    return False


def apply(stem, table, own_tags):
    return [(stem + ending, own_tags + tags) for ending, tags in table]


def is_word(word):
    """A single Latin word: letters and combining marks only (no spaces, hyphens, *)."""
    return bool(word) and all(
        char.isalpha() or unicodedata.combining(char) for char in word
    )
