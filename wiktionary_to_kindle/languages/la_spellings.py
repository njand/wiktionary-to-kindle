"""Other spellings of a Latin entry's forms, which texts use and Wiktionary implies or names
without inflecting (merge.forms, through la.implied_forms).

- Syncopated perfects: amāvisse → amāsse, amāvērunt → amārunt, audīvit → audiit.
- An alternative spelling's inflection: Wiktionary lists Cēphissus beside Cēphīsus and
  abvehō beside āvehō, but only as the headword; every form is respelled alike
  (Cēphissum, abvēxisse).
- Spellings of prefixes and stems that vary between texts: exscindō → excindō, adgemō ↔
  aggemō, adulēscentia ↔ adolēscentia, rettulī → retulī, āfuī → abfuī. A respelled
  headword with a page of the same part of speech is left alone (inlūstris and illūstris
  are two pages).
  Other variants (inclitus/inclytus, Henna/Enna, tōfus/tōphus) would respell letters
  inside every word, and are left to books (prepare-book or the book's own spelling).

Respelled forms are tagged alternative, so the popup lists them after a word spelled that
way by Wiktionary itself.
"""

from ..utils import remove_breves
from .la_forms import is_word

ALTERNATIVE = "alternative"
VOWELS = "aeiouyāēīōūȳ"

# (unassimilated, assimilated) prefixes, at the start of a headword and its forms. A
# headword spelled the second way gets the first only when its etymology names the prefix
# (afferō, from ad-; not annus)
PREFIXES = [
    ("adg", "agg"), ("adc", "acc"), ("adf", "aff"), ("adl", "all"), ("adn", "ann"),
    ("adp", "app"), ("adr", "arr"), ("ads", "ass"), ("adt", "att"),
    ("conl", "coll"), ("conr", "corr"), ("conm", "comm"), ("conb", "comb"),
    ("conp", "comp"),
    ("inl", "ill"), ("inr", "irr"), ("inm", "imm"), ("inb", "imb"), ("inp", "imp"),
    ("obp", "opp"), ("obc", "occ"), ("obf", "off"),
    ("subc", "succ"), ("subf", "suff"), ("subg", "sugg"), ("subm", "summ"),
    ("subp", "supp"), ("subr", "surr"),
]  # fmt: skip
# (written, also written) at the start of a headword and its forms
STARTS = [("exs", "ex"), ("adulēsc", "adolēsc"), ("adolēsc", "adulēsc")]
# (written, also written) at the start of a form, whatever its headword: rettulī (referō),
# āfuī (absum)
FORM_STARTS = [("rettul", "retul"), ("āfu", "abfu")]


def respellings(forms, known, entry, head, alternative_tags):
    """(spelling, tags) of the spellings above, for entry headed head (without breves).
    known holds the dump's headwords without breves."""
    own = [
        {"form": remove_breves(form["form"]), "tags": form.get("tags", [])}
        for form in forms
        if is_word(form.get("form", ""))
        and not alternative_tags & set(form.get("tags", []))
    ]
    implied = syncopated(own)
    for form in forms:
        if alternative_tags & set(form.get("tags", [])) and is_word(form["form"]):
            implied += respelled(own, head, remove_breves(form["form"]))

    etymology = entry.get("etymology_text") or ""
    starts = STARTS + PREFIXES
    starts += [(b, a) for a, b in PREFIXES if a[:-1] + "-" in etymology]
    pos = entry.get("pos")
    for written, also in starts:
        variant = also + head[len(written) :]
        if head.startswith(written) and not _is_word_of(variant, pos, known):
            implied += respelled(own, head, variant)
    for written, also in FORM_STARTS:
        implied += [
            (also + form["form"][len(written) :], form["tags"] + [ALTERNATIVE])
            for form in own
            if form["form"].startswith(written)
            and not _is_word_of(also + form["form"][len(written) :], pos, known)
        ]
    return implied


def _is_word_of(word, pos, known):
    """Whether word has a page with part of speech pos (known: headword -> its parts of
    speech): inlūstris beside illūstris. A page of another part of speech (the participle
    adolēscentia beside the noun adulēscentia) does not count."""
    if not isinstance(known, dict):
        return word in known
    return pos in known.get(word, set())


def respelled(forms, head, variant):
    """(spelling, tags) of forms spelled the way variant spells head: the part where they
    differ is replaced in every form that has it, as long as what follows it in head
    begins the rest of the form (Cēphīsus, Cēphissus: Cēphīsum → Cēphissum)."""
    prefix = 0
    while prefix < min(len(head), len(variant)) and head[prefix] == variant[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < min(len(head), len(variant)) - prefix
        and head[-1 - suffix] == variant[-1 - suffix]
    ):
        suffix += 1
    if not suffix or prefix + suffix < 2:
        return []  # they differ in the ending (catulus, catula) or throughout
    old = head[: len(head) - suffix]
    new = variant[: len(variant) - suffix]
    follows = head[len(head) - suffix]
    return [
        (new + form["form"][len(old) :], form["tags"] + [ALTERNATIVE])
        for form in forms
        if form["form"].startswith(old + follows)
    ]


def syncopated(forms):
    """(spelling, tags) of the syncopated perfects of a perfect in -āvī, -ēvī, -ōvī or -īvī
    (amāsse, amārunt, amārat, nōsse, audīsse, audiit, audiērunt)."""
    stem = _perfect_stem(forms, "v")
    if not stem or len(stem) < 3 or stem[-2] not in "āēōī":
        return []
    implied = []
    for form in forms:
        word = form["form"]
        if not word.startswith(stem):
            continue
        rest = word[len(stem) :]
        if rest.startswith("is"):  # amāvisse → amāsse, audīvistī → audīstī
            spelling = stem[:-1] + rest[1:]
        elif stem[-2] == "ī" and rest[:1] in VOWELS:  # audīvit → audiit
            spelling = stem[:-2] + "i" + rest
        elif rest[:2] in ("er", "ēr") and rest != "ēre":  # amāvērunt → amārunt
            spelling = stem[:-1] + "r" + rest[2:]
        else:
            continue
        implied.append((spelling, form["tags"]))
    return implied


def _perfect_stem(forms, last):
    """The stem of a verb's active perfect (amāv of amāvī) when it ends in last."""
    for form in forms:
        if form.get("tags") == ["active", "perfect"]:
            word = remove_breves(form["form"])
            if word.endswith(last + "ī"):
                return word[:-1]
    return None
