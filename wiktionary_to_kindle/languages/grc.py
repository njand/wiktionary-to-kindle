"""Ancient Greek: the spellings a tap should find, and why a word in a Greek text opens
nothing.

A Kindle folds no Greek letter: case and accents count, so every spelling a text prints
must be a label of its own. Wiktionary's headwords and table forms carry length marks (ᾱ,
ῠ), which texts never print; texts print a grave for a final acute before another word,
and capitals at the start of a paragraph or a speech.
"""

import unicodedata

from ..utils import BREVE, MACRON
from . import Language

GRAVE, ACUTE, CIRCUMFLEX = "\u0300", "\u0301", "\u0342"
VOWELS = set("αεηιουω")


def strip_length(text: str) -> str:
    """text without macrons and breves, keeping accents and breathings: λῡ̆́ω → λύω."""
    decomposed = unicodedata.normalize("NFD", text)
    kept = "".join(c for c in decomposed if c not in (MACRON, BREVE))
    return unicodedata.normalize("NFC", kept)


def with_grave(word: str) -> str:
    """word with the acute on its last syllable written as a grave, as a text prints it
    before another word (καλός → καλὸς). Unchanged when the acute is not on the last
    syllable or there is none."""
    decomposed = unicodedata.normalize("NFD", word)
    accent = decomposed.rfind(ACUTE)
    if accent == -1 or any(c in VOWELS for c in decomposed[accent + 1 :].lower()):
        return word
    graved = decomposed[:accent] + GRAVE + decomposed[accent + 1 :]
    return unicodedata.normalize("NFC", graved)


def lookup_spellings(form: str) -> list[str]:
    """The spellings of form a Greek text prints: without length marks, and with a grave
    for a final acute. The spelling with length marks is no label: no text prints it.
    Capitals are added for some entries only (capitalizes)."""
    plain = strip_length(form)
    return list(dict.fromkeys([plain, with_grave(plain)]))


# Words that open a sentence or a speech often enough for their capitalized spellings to
# pay for their labels: the article, pronouns, particles, conjunctions, prepositions
CAPITALIZED_POS = {"pron", "det", "conj", "particle", "prep", "adv", "intj", "num"}


def capitalizes(pos, headword):
    """Whether a spelling also gets its capitalized form: every headword, and every form
    of a word in CAPITALIZED_POS. Capitalizing every form doubled the labels for 0.8% of
    corpus tokens (roadmap, Stage 9)."""
    return headword or pos in CAPITALIZED_POS


def implied_forms(forms, known):
    return []


# Elision marks: the modifier apostrophe Perseus prints, the quotation mark, the koronis
ELISION_MARKS = "\u02bc\u2019'\u1fbd"
# Before a rough breathing an elided word's last consonant is aspirated: καθʼ for κατά
DEASPIRATE = str.maketrans("θφχ", "τπκ")
ELIDED_VOWELS = ("α", "ε", "ι", "ο", "ά", "έ", "ί", "ό")


def miss_variants(word):
    """(causes, variant) for the spellings a Greek text prints but Wiktionary's forms do
    not: oxia or decomposed accents, a capital, a grave for an acute, the second accent an
    enclitic puts on the word before it, movable nu, elision. A Kindle folds none of them.
    Crasis and dialect forms are not guessed."""
    variants = [((), word)]
    for cause, respell in (
        ("oxia or decomposed", lambda w: [unicodedata.normalize("NFC", w)]),
        ("capitalized", lambda w: [w[:1].lower() + w[1:]]),
        ("grave for acute", lambda w: [_with_marks(w, {GRAVE: ACUTE})]),
        ("enclitic's accent", lambda w: [_without_second_accent(w)]),
        ("movable nu", _movable_nu),
        ("elision", _unelided),
    ):
        variants += [
            (causes + (cause,), new)
            for causes, old in list(variants)
            for new in respell(old)
            if new != old
        ]
    return [variant for variant in variants if variant[0]]


def _with_marks(word, replace):
    decomposed = unicodedata.normalize("NFD", word)
    marks = "".join(replace.get(c, c) for c in decomposed)
    return unicodedata.normalize("NFC", marks)


def _without_second_accent(word):
    """ἄνθρωπός (before τις) as ἄνθρωπος: of two accents, the last acute goes."""
    decomposed = unicodedata.normalize("NFD", word)
    accents = [i for i, c in enumerate(decomposed) if c in (ACUTE, GRAVE, CIRCUMFLEX)]
    if len(accents) < 2 or decomposed[accents[-1]] == CIRCUMFLEX:
        return word
    last = accents[-1]
    return unicodedata.normalize("NFC", decomposed[:last] + decomposed[last + 1 :])


def _movable_nu(word):
    """ἐστίν, ἔλυσεν, πᾶσιν without their ν, and the reverse. Only -ε, -σι and -στι take
    one: an accusative's ν (χώραν) or an infinitive's (λαλεῖν) is none."""
    letters = "".join(unicodedata.normalize("NFD", c)[0] for c in word)
    if letters.endswith(("εν", "σιν", "στιν")):
        return [word[:-1]]
    if letters.endswith(("ε", "σι", "στι")):
        return [word + "ν"]
    return []


def _unelided(word):
    """The words an elided word (δʼ, ἀλλʼ, καθʼ) may stand for: each short vowel, with an
    acute when the rest has no accent, after the consonant with its aspiration undone."""
    if len(word) < 2 or word[-1] not in ELISION_MARKS:
        return []
    bases = list(dict.fromkeys([word[:-1], word[:-1].translate(DEASPIRATE)]))
    accented = any(
        c in (ACUTE, GRAVE, CIRCUMFLEX) for c in unicodedata.normalize("NFD", word)
    )
    vowels = ELIDED_VOWELS[:4] if accented else ELIDED_VOWELS
    return [base + vowel for base in bases for vowel in vowels]


ANCIENT_GREEK = Language(
    code="grc",
    name="Ancient Greek",
    index_name="Greek",
    lookup_spellings=lookup_spellings,
    capitalizes=capitalizes,
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
