"""The forms a Turkish word implies that no Wiktionary table lists: the copula (kadındı,
yıllardır, oğluydu, vardır: was, is), -(y)lA "with" (sesle, onlarla, nedeniyle) and -ki
"the one in" (dünyadaki, arasındaki, sonraki).

They are suffixes on a noun's nominative or locative, or on an adjective, adverb or
postposition, by vowel harmony: -(y)DI (past), -DIr (present) and -(y)lA, where y follows a
vowel, D is t after a voiceless consonant, I is ı, i, u or ü and A is a or e by the last
vowel; -ki does not change. A loanword's nominative may take front suffixes after a back
vowel (saat, saatte): its own dative or locative says which. Adjectives with a table
already list their copula forms (güzeldim).

Each kind was measured on the Turkish corpus first, as missed tokens its forms would open
per label, and only those that paid are generated. Not generated: the
evidential -(y)mIş, the conditional -(y)sA, -(y)ken, the copula on other cases (evdeydi),
any of these on a first- or second-person possessive (evimdi, elimle, evimdeki), and -ki on
a genitive (bizimki).
"""

import unicodedata

# Suffixes on a nominative: (template, tags). y: buffer after a vowel; D: d or t; I and A:
# vowels by harmony
NOMINATIVE_SUFFIXES = (
    ("yDI", ["copula", "past"]),
    ("DIr", ["copula", "present"]),
    ("ylA", ["instrumental"]),
)
LOCATIVE_SUFFIXES = (("ki", ["relative"]),)
# The suffixes a headword without case forms takes, by its part of speech: vardır,
# demektir, gibiydi, budur, aceleyle, sonraki, oradaki
BARE_SUFFIXES = {
    "adj": NOMINATIVE_SUFFIXES,
    "adv": NOMINATIVE_SUFFIXES + LOCATIVE_SUFFIXES,
    "postp": NOMINATIVE_SUFFIXES[:2] + LOCATIVE_SUFFIXES,
    "det": NOMINATIVE_SUFFIXES[:2],
}
COPULA = NOMINATIVE_SUFFIXES[:2]
CASES = {"nominative", "accusative", "dative", "locative", "ablative", "genitive"}
BACK, FRONT = set("aıou"), set("eiöü")
ROUNDED = set("ouöü")
VOICELESS = set("çfhkpsştÇFHKPSŞT")
PLAIN_VOWELS = str.maketrans("âîûÂÎÛ", "aiuAIU")


def implied_forms(forms, known, entry):
    """(spelling, tags) of the copula and -(y)lA on an entry's nominatives, and -ki on its
    locatives, without a possessor or with a third-person one (kadın-dı, ses-le, el-i-yle,
    dünya-da-ki, ara-sı-nda-ki); or of the suffixes BARE_SUFFIXES gives its headword when
    it is an adjective, adverb, postposition or determiner without case forms (var-dır,
    sonra-ki)."""
    by_tags = {frozenset(form.get("tags", [])): form.get("form", "") for form in forms}
    bases = []  # (base, its tags, suffixes, front)
    for form in forms:
        word, tags = form.get("form", ""), set(form.get("tags", []))
        if tags & {"copula", "instrumental", "relative", "predicative"}:
            continue
        if "possessive" in tags and "third-person" not in tags:
            continue
        if "nominative" in tags:
            front = None
            if tags == {"nominative", "singular"}:
                front = _front_suffix(word, by_tags)
            bases.append((word, tags - {"nominative"}, NOMINATIVE_SUFFIXES, front))
        elif "locative" in tags:
            bases.append((word, tags, LOCATIVE_SUFFIXES, None))
    pos = entry.get("pos")
    if (
        pos in BARE_SUFFIXES
        and not any(set(form.get("tags", [])) & CASES for form in forms)
        and not _only_points(entry)
    ):
        bases.append((entry.get("word", ""), set(), BARE_SUFFIXES[pos], None))
    implied = []
    for base, tags, suffixes, front in bases:
        if not base.replace("'", "").isalpha():
            continue
        for template, suffix_tags in suffixes:
            spelling = attach(base, template, front)
            if spelling:
                implied.append((spelling, [*sorted(tags), *suffix_tags]))
    return implied + [(stem, ["stem-variant"]) for stem in stem_variants(forms, entry)]


def stem_variants(forms, entry):
    """The stems an entry's suffixed forms are built on where they differ from its
    headword, which a book split leaves before a hair space: kitab (kitabı, of kitap),
    ağz (ağzı), hakk (hakkı), gid (gidiyor, of gitmek), bekli (bekliyor, of beklemek).
    Read off the entry's own forms, so no rule guesses them."""
    word = entry.get("word", "")
    spellings = {form.get("form", "") for form in forms}
    variants = []
    if entry.get("pos") == "verb" and word.endswith(("mek", "mak")):
        stem = word[:-3]
        for vowel in "ıiuü":
            if stem and stem[-1] in "ae":
                # Narrowing: bekle-, bekliyor
                narrowed = stem[:-1] + vowel
                if narrowed + "yor" in spellings:
                    variants.append(narrowed)
            elif stem:
                # A voiced final consonant: git-, gidiyor
                for form in spellings:
                    voiced = form[: -len(vowel + "yor")]
                    if (
                        form.endswith(vowel + "yor")
                        and len(voiced) == len(stem)
                        and voiced[:-1] == stem[:-1]
                        and voiced != stem
                    ):
                        variants.append(voiced)
    else:
        nominative = _form(forms, {"nominative", "singular"})
        accusative = _form(forms, {"accusative", "definite", "singular"})
        if (
            nominative
            and accusative
            and nominative[-1] not in BACK | FRONT
            and accusative[-1] in BACK | FRONT
            and accusative[:-1] != nominative
        ):
            variants.append(accusative[:-1])
    # A name's apostrophe (NATO'yu) and a phrase's space leave no stem to split after
    variants = [v for v in variants if v and v != word and v.isalpha()]
    return list(dict.fromkeys(variants))


def _form(forms, tags):
    return next(
        (f.get("form", "") for f in forms if set(f.get("tags", [])) == tags), ""
    )


def _only_points(entry):
    """Whether every sense of a page only points to a lemma (a form-of page)."""
    senses = entry.get("senses") or []
    return bool(senses) and all("form_of" in s or "alt_of" in s for s in senses)


def copula(base, front=None):
    """(spelling, tags) of the copula on base; front overrides the harmony its last vowel
    gives (True for saat, whose suffixes are front)."""
    spellings = [(attach(base, template, front), tags) for template, tags in COPULA]
    return [(spelling, tags) for spelling, tags in spellings if spelling]


def attach(base, template, front=None):
    """base with a suffix template by vowel harmony (y: buffer after a vowel; D: d or t;
    I: ı, i, u or ü; A: a or e), or None when base writes no vowel (an abbreviation: AB,
    TBMM). front overrides the harmony base's last vowel gives."""
    vowels = [c for c in _letters(base) if c in BACK | FRONT]
    if not vowels:
        return None
    last = vowels[-1]
    is_front = last in FRONT if front is None else front
    rounded = last in ROUNDED
    ends_vowel = _letters(base)[-1] in BACK | FRONT
    voiceless = base[-1] in VOICELESS
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
    return base + suffix


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
