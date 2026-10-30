"""The copula forms a Turkish word implies, which no Wiktionary table lists: kadındı,
yıllardır, oğluydu, konusudur, vardır, gibiydi (was, is).

The copula is a suffix on a noun's case forms, or on an adjective, adverb or postposition,
by vowel harmony: -(y)DI (past) and -DIr (present), where y follows a vowel, D is t after a
voiceless consonant and I is ı, i, u or ü by the last vowel. A loanword's nominative may
take front suffixes after a back vowel (saat, saatte): its own dative or locative says
which. Adjectives with a table already list their copula forms (güzeldim).

Measured on the Stage 12 corpus (roadmap, Stage 13): these open 0.5% more tokens for 94K
labels. The evidential -(y)mIş, the conditional -(y)sA, -(y)ken, and the copula on other
cases (evdeydi) or other possessors (evimdi) together opened about 0.2% for 3.8M more, so
they are not generated.
"""

import unicodedata

# Copula suffixes: (template, tags). y: buffer after a vowel; D: d or t; I and A: vowels
COPULA = (("yDI", ["past"]), ("DIr", ["present"]))
# Parts of speech whose headword takes the copula when the entry has no table: vardır,
# demektir, gibiydi, budur
BARE_POS = {"adj", "adv", "postp", "det"}
CASES = {"nominative", "accusative", "dative", "locative", "ablative", "genitive"}
BACK, FRONT = set("aıou"), set("eiöü")
ROUNDED = set("ouöü")
VOICELESS = set("çfhkpsştÇFHKPSŞT")
PLAIN_VOWELS = str.maketrans("âîûÂÎÛ", "aiuAIU")


def implied_forms(forms, known, entry):
    """(spelling, tags) of the copula on an entry's nominatives without a possessor or
    with a third-person one (kadın-dı, oğlu-ydu), or on its headword when it is an
    adjective, adverb, postposition or determiner without case forms (var-dır)."""
    by_tags = {frozenset(form.get("tags", [])): form.get("form", "") for form in forms}
    bases = []
    for form in forms:
        word, tags = form.get("form", ""), set(form.get("tags", []))
        if "nominative" not in tags or "copula" in tags:
            continue
        if "possessive" in tags and "third-person" not in tags:
            continue
        front = None
        if tags == {"nominative", "singular"}:
            front = _front_suffix(word, by_tags)
        bases.append((word, sorted(tags - {"nominative"}), front))
    word = entry.get("word", "")
    if (
        entry.get("pos") in BARE_POS
        and not any(set(form.get("tags", [])) & CASES for form in forms)
        and not _only_points(entry)
    ):
        bases.append((word, [], None))
    implied = []
    for base, tags, front in bases:
        if base.replace("'", "").isalpha():
            implied += [
                (spelling, [*tags, "copula", *copula_tags])
                for spelling, copula_tags in copula(base, front)
            ]
    return implied


def _only_points(entry):
    """Whether every sense of a page only points to a lemma (a form-of page)."""
    senses = entry.get("senses") or []
    return bool(senses) and all("form_of" in s or "alt_of" in s for s in senses)


def copula(base, front=None):
    """(spelling, tags) of the copula on base; front overrides the harmony its last vowel
    gives (True for saat, whose suffixes are front)."""
    vowels = [c for c in _letters(base) if c in BACK | FRONT]
    if not vowels:
        return []  # an abbreviation (AB, TBMM): its vowels are not written
    last = vowels[-1]
    is_front = last in FRONT if front is None else front
    rounded = last in ROUNDED
    ends_vowel = _letters(base)[-1] in BACK | FRONT
    voiceless = base[-1] in VOICELESS
    spellings = []
    for template, tags in COPULA:
        suffix = ""
        for char in template:
            if char == "y":
                suffix += "y" if ends_vowel else ""
            elif char == "D":
                suffix += "t" if voiceless else "d"
            elif char == "I":
                suffix += ("üi" if is_front else "uı")[0 if rounded else 1]
            elif char == "A":
                suffix += "e" if is_front else "a"
            else:
                suffix += char
        spellings.append((base + suffix, tags))
    return spellings


def _front_suffix(word, by_tags):
    """Whether a nominative takes front suffixes, from its dative or locative singular
    (saate, saatte), or None when neither is listed."""
    for case in ("dative", "locative"):
        inflected = by_tags.get(frozenset({case, "singular"}), "")
        if inflected.startswith(word) and len(inflected) > len(word):
            return inflected[-1] in FRONT
    return None


def _letters(word):
    """word in lowercase, without apostrophes or circumflexes: the letters harmony reads."""
    word = unicodedata.normalize("NFC", word).translate(PLAIN_VOWELS)
    return (
        word.replace("'", "")
        .replace("’", "")
        .replace("I", "ı")
        .replace("İ", "i")
        .lower()
    )
