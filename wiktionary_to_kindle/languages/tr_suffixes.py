"""Turkish suffix chains: every chain a book split may leave after a stem, spelled as it
follows each kind of stem, with its analysis (lerimizden: plural + our + from).

prepare-book splits a word the dictionary cannot reach into its stem and its suffix chain
with a hair space; a tap on the chain then opens the chain's own entry (roadmap, Stage 15).
The same chains decide which splits are possible at all: a split must leave a chain this
grammar makes for that kind of stem.

Morphemes are written with archiphonemes, filled in by vowel harmony as they are
attached: A is a or e, I is ı, i, u or ü by the vowel before; D is d or t, C is c or ç
(t and ç after a voiceless consonant); K is k, or ğ before a vowel. A letter in brackets is
written only after a vowel, (y), (n), (s), or only after a consonant, (I), (A). A vowel A
before the progressive (I)yor narrows to I (bekle-r, bekl-iyor; gel-me, gel-m-iyor).

Of the voice suffixes only the passive is chained (bekle-n-iyor: n after a vowel, In
after l, Il otherwise), since Wiktionary lacks many passives; causatives and reciprocals
are mostly words of their own (yazdırmak). A few derivational suffixes (-lI, -sIz, -lIk,
-CI, -CA, -CIK) are chained on nouns with a short tail (bulut-suz, gözlükçü-ler).
"""

from dataclasses import dataclass
from functools import cache
from itertools import product

BACK, FRONT = set("aıou"), set("eiöü")
VOWELS = BACK | FRONT
ROUNDED = set("ouöü")
VOICELESS = set("çfhkpsşt")


@dataclass(frozen=True)
class Morpheme:
    template: str
    gloss: str


def m(template, gloss):
    return Morpheme(template, gloss)


PLURAL = m("lAr", "plural")
POSSESSIVES = (
    m("(I)m", "my"),
    m("(I)n", "your"),
    m("(s)I", "his/her/its"),
    m("(I)mIz", "our"),
    m("(I)nIz", "your (pl.)"),
    m("lArI", "their"),
)
CASES = (
    m("(y)I", "definite object (acc.)"),
    m("(y)A", "to (dat.)"),
    m("DA", "in, at (loc.)"),
    m("DAn", "from (abl.)"),
    m("(n)In", "of (gen.)"),
    m("(y)lA", "with"),
)
# After a third-person possessive a case takes n: evi-ni, evi-ne, evi-nde, evi-nden
CASES_AFTER_3RD = (
    m("nI", "definite object (acc.)"),
    m("nA", "to (dat.)"),
    m("ndA", "in, at (loc.)"),
    m("ndAn", "from (abl.)"),
    m("nIn", "of (gen.)"),
    m("(y)lA", "with"),
)
KI = m("ki", "the one (that is) … (-ki)")
# The persons of the copula and of most tenses (z-type), and of the past and conditional
Z_PERSONS = (
    m("(y)Im", "I"),
    m("sIn", "you"),
    None,
    m("(y)Iz", "we"),
    m("sInIz", "you (pl.)"),
    m("lAr", "they"),
)
K_PERSONS = (
    m("m", "I"),
    m("n", "you"),
    None,
    m("k", "we"),
    m("nIz", "you (pl.)"),
    m("lAr", "they"),
)
COPULAS = (
    (m("(y)DI", "was"), K_PERSONS),
    (m("(y)mIş", "is said to be (evidential)"), Z_PERSONS),
    (m("(y)sA", "if … is"), K_PERSONS),
)
PRESENT_COPULA = m("DIr", "is (generalizing)")
WHILE = m("(y)ken", "while")

# Derivational suffixes on a noun, with the few suffixes chained after them
DERIVATIONS = (
    m("lI", "with, having (-lI)"),
    m("sIz", "without (-sIz)"),
    m("lIK", "-ness, a place or thing for (-lIk)"),
    m("CI", "one who makes, sells or does (-CI)"),
    m("CA", "in the manner of, the language of (-CA)"),
    m("CIK", "little (-CIk)"),
)
PASSIVE = m("P", "is …ed (passive)")
NEGATIVE = m("mA", "not")
ABILITY = m("(y)Abil", "can")
INABILITY = m("(y)AmA", "cannot")
# (tense, its persons, whether a copula may follow)
TENSES = (
    (m("(I)yor", "is …ing (progressive)"), Z_PERSONS, True),
    (m("(A)r", "does (aorist)"), Z_PERSONS, True),
    (m("(I)r", "does (aorist)"), Z_PERSONS, True),
    (m("DI", "did (past)"), K_PERSONS, False),
    (m("mIş", "did, it seems (evidential past)"), Z_PERSONS, True),
    (m("(y)AcAK", "will (future)"), Z_PERSONS, True),
    (m("mAlI", "must"), Z_PERSONS, True),
    (m("sA", "if (conditional)"), K_PERSONS, False),
)
NEGATIVE_AORIST = (
    m("mAm", "I do not"),
    m("mAzsIn", "you do not"),
    m("mAz", "does not"),
    m("mAyIz", "we do not"),
    m("mAzsInIz", "you (pl.) do not"),
    m("mAzlAr", "they do not"),
)
IMPERATIVES = (
    m("sIn", "let him/her …"),
    m("(y)In", "… ! (pl. or polite)"),
    m("(y)InIz", "… ! (pl. or polite)"),
    m("sInlAr", "let them …"),
    m("(y)AlIm", "let us …"),
)
# Verbal nouns and participles take a noun's possessives and cases
NOMINALIZERS = (
    m("mA", "…ing (verbal noun)"),
    m("(y)Iş", "way of …ing"),
    m("DIK", "that … did/does (participle)"),
    m("(y)AcAK", "that … will (future participle)"),
)
PARTICIPLE = m("(y)An", "who/which …es (participle)")
INFINITIVES = (
    m("mAK", "to … (infinitive)"),
    m("mAktA", "is …ing (formal progressive)"),
    m("mAktAn", "from …ing"),
    m("mAyA", "to …ing (dat.)"),
    m("mAklA", "with …ing"),
)
CONVERBS = (
    m("(y)Ip", "and (then)"),
    m("(y)ArAk", "by …ing"),
    m("(y)IncA", "when"),
    m("mAdAn", "without …ing"),
    m("(y)AlI", "since"),
    m("DIkçA", "the more … / whenever"),
    m("(A)rkAn", "while …ing"),
    m("(I)rkAn", "while …ing"),
    m("(y)ken", "while"),
    m("(y)AsIyA", "until"),
)


def _optional(xs):
    return (None, *xs)


def noun_chains(include_plural=True, copula=True):
    """Every nominal chain: (plural) (possessive) (case | loc or gen + -ki ...)
    (copula with its person), as tuples of Morphemes; without the copula when copula is
    false (after a verbal noun or participle, where it is rare)."""
    chains = []
    for plural in _optional([PLURAL] if include_plural else []):
        for possessive in _optional(POSSESSIVES):
            if possessive is not None and possessive.template == "lArI" and plural:
                continue  # their: evleri, not evlerleri
            third = possessive is not None and possessive.gloss in (
                "his/her/its",
                "their",
            )
            cases = CASES_AFTER_3RD if third else CASES
            base = [x for x in (plural, possessive) if x]
            for case in _optional(cases):
                head = base + ([case] if case else [])
                chains.append(head)
                if case and case.gloss in ("in, at (loc.)", "of (gen.)"):
                    for ki_plural in _optional([PLURAL]):
                        # evdeki-ni, but evdekiler-i
                        ki_cases = CASES if ki_plural else CASES_AFTER_3RD
                        for ki_case in _optional(ki_cases):
                            tail = [x for x in (KI, ki_plural, ki_case) if x]
                            chains.append(head + tail)
    if not copula:
        return [tuple(chain) for chain in chains if chain]
    with_copula = []
    for chain in chains:
        with_copula.append(chain)
        if chain and chain[-1].gloss == "definite object (acc.)":
            continue  # an accusative takes no copula
        with_copula.append(chain + [PRESENT_COPULA])
        with_copula.append(chain + [WHILE])
        for copula_morpheme, persons in COPULAS:
            for person in persons:
                with_copula.append(chain + [x for x in (copula_morpheme, person) if x])
        for person in Z_PERSONS:
            if person and chain:
                with_copula.append(chain + [person])
    return [tuple(chain) for chain in with_copula if chain]


def derived_chains():
    """A derivational suffix, then nothing, a plural, a case, the plural and a case, a
    third-person possessive, or the copula's is or was: bulut-suz, gözlük-çü-ler."""
    tails = [[], [PLURAL], [POSSESSIVES[2]], [PRESENT_COPULA], [COPULAS[0][0]]]
    tails += [[case] for case in CASES] + [[PLURAL, case] for case in CASES]
    return [(d, *tail) for d in DERIVATIONS for tail in tails]


def verb_chains():
    """Every verbal chain: (not) (can | cannot) tense person (copula person), the
    imperatives, and the verbal nouns, participles, infinitives and converbs with their
    own suffixes."""
    chains = []
    noun_tails = noun_chains(include_plural=False, copula=False)
    participle_tails = noun_chains(copula=False)
    for voice, negative, ability in product(
        (None, PASSIVE), (None, NEGATIVE), (None, ABILITY, INABILITY)
    ):
        if negative and ability:
            continue
        head = [x for x in (voice, negative, ability) if x]
        if True:
            for tense, persons, takes_copula in TENSES:
                for person in persons:
                    chain = head + [x for x in (tense, person) if x]
                    chains.append(chain)
                if takes_copula:
                    for copula, copula_persons in COPULAS:
                        for person in copula_persons:
                            chains.append(
                                head + [x for x in (tense, copula, person) if x]
                            )
            if not negative and not ability:
                chains += [head + [form] for form in NEGATIVE_AORIST]
                chains += [head + [form] for form in IMPERATIVES]
                if voice:
                    chains.append(head)  # the passive stem's imperative: beklen
            elif negative:
                chains.append(head)  # the negative imperative: gelme
            for nominalizer in NOMINALIZERS:
                chains.append(head + [nominalizer])
                chains += [head + [nominalizer, *tail] for tail in noun_tails]
            chains.append(head + [PARTICIPLE])
            chains += [head + [PARTICIPLE, *tail] for tail in participle_tails]
            chains += [head + [infinitive] for infinitive in INFINITIVES]
            chains += [head + [converb] for converb in CONVERBS]
    return [tuple(chain) for chain in chains if chain]


def attach(word, morphemes):
    """word with the morphemes attached by vowel harmony, or None when the result is
    not a spelling (a narrowed vowel that belongs to the stem)."""
    out = word
    k_soft = False  # the last letter is a K that softens to ğ before a vowel
    for morpheme in morphemes:
        template = morpheme.template
        if template == "P":
            # The passive: bekle-n, bil-in, yaz-ıl
            ends_vowel = bool(out) and out[-1] in VOWELS
            template = "n" if ends_vowel else "In" if out.endswith("l") else "Il"
        if template.startswith("(I)yor") and out and out[-1] in "ae":
            # Narrowing: gel-me-yor is gelmiyor
            out = out[:-1]
            template = "I" + template[3:]
        pieces = _units(template)
        for i, (unit, optional) in enumerate(pieces):
            ends_vowel = bool(out) and out[-1] in VOWELS
            if optional and unit in "yns" and not ends_vowel:
                continue
            if optional and unit in "AI" and ends_vowel:
                continue
            letter = _letter(out, unit)
            if letter in VOWELS and k_soft:
                out = out[:-1] + "ğ"
            k_soft = unit == "K"
            out += letter
    return out


def _units(template):
    units, i = [], 0
    while i < len(template):
        if template[i] == "(":
            units.append((template[i + 1], True))
            i += 3
        else:
            units.append((template[i], False))
            i += 1
    return units


def _letter(word, unit):
    vowels = [c for c in word if c in VOWELS]
    last = vowels[-1] if vowels else "e"
    front, rounded = last in FRONT, last in ROUNDED
    voiceless = bool(word) and word[-1] in VOICELESS
    if unit == "A":
        return "e" if front else "a"
    if unit == "I":
        return ("üi" if front else "uı")[0 if rounded else 1]
    if unit == "D":
        return "t" if voiceless else "d"
    if unit == "C":
        return "ç" if voiceless else "c"
    if unit == "K":
        return "k"
    return unit


def stem_class(stem):
    """What a chain's spelling depends on: the stem's last vowel, and whether it ends in
    a vowel, a voiceless consonant, an l or another consonant."""
    letters = stem.lower().replace("'", "").replace("’", "")
    letters = letters.translate(str.maketrans("âîûI", "aiuı"))
    vowels = [c for c in letters if c in VOWELS]
    last = vowels[-1] if vowels else "e"
    end = letters[-1:] or "a"
    if end in VOWELS:
        kind = "vowel"
    elif end in VOICELESS:
        kind = "voiceless"
    else:
        kind = (
            "l" if end == "l" else "voiced"
        )  # the passive is -In after l, -Il after r
    return last, kind


# A stem for each class, to spell the chains with: (last vowel, ending) -> stem
SAMPLE_ENDINGS = {"vowel": "", "voiceless": "t", "voiced": "r", "l": "l"}


@cache
def chains_for(cls):
    """{chain spelling: [analysis, ...]} for a stem of class cls (stem_class)."""
    vowel, kind = cls
    stem = "b" + vowel + SAMPLE_ENDINGS[kind]
    spelled = {}
    for chain in noun_chains() + derived_chains() + verb_chains():
        word = attach(stem, chain)
        if not word.startswith(stem) or len(word) == len(stem):
            continue
        rest = word[len(stem) :]
        gloss = " + ".join(morpheme.gloss for morpheme in chain)
        spelled.setdefault(rest, [])
        if gloss not in spelled[rest]:
            spelled[rest].append(gloss)
    return spelled


def all_chains():
    """{chain spelling: [analysis, ...]} over every class of stem."""
    merged = {}
    for vowel in sorted(VOWELS):
        for kind in SAMPLE_ENDINGS:
            for rest, glosses in chains_for((vowel, kind)).items():
                merged.setdefault(rest, [])
                merged[rest] += [g for g in glosses if g not in merged[rest]]
    return merged


def suffix_entries():
    """A Kaikki-shaped entry per chain spelling, filed as -lerimizden, with an analysis
    per sense. The hyphen weighs nothing on the device, so a tap on lerimizden reaches
    it, but a word spelled like a chain (de, in) is listed first."""
    for rest, glosses in sorted(all_chains().items()):
        word = "-" + rest
        yield {
            "word": word,
            "pos": "suffix",
            "lang_code": "tr",
            "lang": "Turkish",
            "head_templates": [{"name": "head", "expansion": word}],
            "senses": [{"glosses": [gloss]} for gloss in glosses],
            "suffix_chain": True,
        }
