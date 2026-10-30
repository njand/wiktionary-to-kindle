"""The comparative, superlative and adverb a Latin adjective implies but Wiktionary does not
list (merge.forms, through la.implied_forms).

Wiktionary names an adjective's comparative, superlative and adverb in its head line only
where a source attests them: serēnus names neither comparative nor superlative, blandus no
superlative, officiōsus no adverb. Texts still use them (serēnissima, blandissimus), so the
regular ones are generated: -ior and -issimus (-errimus after -er, -illimus for the six in
-ilis), -ē after a first/second-declension stem, -iter after a third-declension one (-er
after -nt). Participles used as adjectives are compared too (praesentior,
convenientissimus): those with a sense of their own, or an adverb or comparison listed.

Left out: adjectives that are comparatives or superlatives themselves (superior, optimus),
stems ending in a vowel (idōneus: magis idōneus), relational and proper adjectives
(Rōmānus, Athēniēnsis, marīnus, bellicus, nātūrālis, frūgifer), gerundives, and a
generated form with an adjective or adverb page.
A generated spelling that is another entry's word (blandior, also a verb) is listed after
it in the popup (render.popup_order weighs generated forms low).
"""

from ..utils import normalize, remove_breves
from .la_forms import COMPARATIVE, FIRST_SECOND, NOM, SG, VOC, F, M, apply

# Adjectives whose superlative is -illimus (facillimus); other -ilis ones take -issimus
ILLIMUS = {"facilis", "difficilis", "similis", "dissimilis", "gracilis", "humilis"}
# Relational adjectives and compounds in -fer, -ger: compared only by magis, if at all.
# Matched without macrons, except -icus, which is matched short (bellicus, not pudīcus)
RELATIONAL = ("anus", "ensis", "arius", "orius", "inus", "alis", "aris", "fer", "ger")
SKIPPED_TAGS = {"comparative", "superlative", "not-comparable", "possessive"}
COMPARED = (["adverb"], ["comparative"], ["superlative"])


def comparison(forms, known, entry):
    """(spelling, tags) of the comparative, superlative and adverb entry (an adjective or
    participle page) implies and does not list."""
    stems = _stems(forms, entry)
    if stems is None:
        return []
    stem, superlative, adverb = stems
    listed = {form["tags"][0] for form in forms if len(form.get("tags", [])) == 1}

    implied = []
    if "comparative" not in listed and not _has_page(stem + "ior", known):
        implied.append((stem + "ior", ["comparative"]))
        implied.append((stem + "ior", ["comparative", M, F, NOM, VOC, SG]))
        implied += apply(stem, COMPARATIVE, ["comparative"])
    if "superlative" not in listed and not _has_page(superlative + "us", known):
        implied.append((superlative + "us", ["superlative"]))
        implied += apply(superlative, FIRST_SECOND, ["superlative"])
        implied.append((superlative + "ē", ["adverb", "superlative"]))
    if "adverb" not in listed and not _has_page(adverb, known):
        implied.append((adverb, ["adverb"]))
    return implied


def _stems(forms, entry):
    """(comparative stem, superlative stem, adverb) of an adjective or participle page, or
    None when it is not one that compares regularly."""
    head_templates = entry.get("head_templates") or [{}]
    template = head_templates[0].get("name")
    if template not in ("la-adj", "la-part"):
        return None
    senses = entry.get("senses", [])
    # A participle only (amātus) is compared when Wiktionary compares it or gives it an
    # adverb (conveniēns, convenienter)
    if (
        template == "la-part"
        and all("form_of" in sense for sense in senses)
        and not any(form.get("tags") in COMPARED for form in forms)
    ):
        return None
    tags = {tag for sense in senses for tag in sense.get("tags", [])}
    if tags & SKIPPED_TAGS:
        return None
    word = remove_breves(head_templates[0].get("expansion", "").split(" ")[0])
    plain = normalize(word)
    if not word.isalpha() or not plain.islower() or plain.endswith(RELATIONAL):
        return None
    if word.endswith("icus") or (template == "la-part" and plain.endswith("ndus")):
        return None  # bellicus; a gerundive (amandus)

    by_tag = {}
    for form in forms:
        if len(form.get("tags", [])) == 1:
            by_tag.setdefault(form["tags"][0], remove_breves(form.get("form", "")))
    feminine, genitive, neuter = (
        by_tag.get("feminine", ""),
        by_tag.get("genitive", ""),
        by_tag.get("neuter", ""),
    )

    if "declension-3" in tags:
        if genitive.endswith("is"):  # prūdēns, prūdentis; pervicāx, pervicācis
            stem = genitive[:-2]
        elif feminine.endswith("is"):  # ācer, ācris
            stem = feminine[:-2]
        elif plain.endswith("is") and neuter.endswith("e"):  # fortis, forte
            stem = word[:-2]
        else:
            return None
        adverb = stem + ("er" if normalize(stem).endswith("nt") else "iter")
    elif plain.endswith("us"):
        stem, adverb = word[:-2], word[:-2] + "ē"
    elif plain.endswith("er") and feminine.endswith("a"):  # pulcher, pulchra
        stem, adverb = feminine[:-1], feminine[:-1] + "ē"
    else:
        return None

    plain_stem = normalize(stem).lower()
    if not plain_stem or (plain_stem[-1] in "aeiouy" and not plain_stem.endswith("qu")):
        return None
    if plain.endswith("er"):
        superlative = word + "rim"  # pulcherrimus, ācerrimus
    elif plain in ILLIMUS:
        superlative = stem + "lim"  # facillimus
    else:
        superlative = stem + "issim"
    return stem, superlative, adverb


def _has_page(word, known):
    """Whether word has an adjective or adverb page (known: headword -> its parts of
    speech). Another word spelled alike (praesentior, of praesentiō) does not count."""
    word = remove_breves(word)
    if not isinstance(known, dict):
        return word in known
    return bool(known.get(word, set()) & {"adj", "adv"})
