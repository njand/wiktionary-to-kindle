"""Ancient Greek: the spellings a tap should find, and why a word in a Greek text opens
nothing.

A Kindle folds no Greek letter: case and accents count, so every spelling a text prints
must be a label of its own. Wiktionary's headwords and table forms carry length marks (ᾱ,
ῠ): most editions print none, school editions mark the long vowels, so both spellings are
labels. Texts print a grave for a final acute before another word, and capitals at the
start of a paragraph or a speech.
"""

import re
import unicodedata
from itertools import product

from ..utils import BREVE, MACRON
from . import Language, unrecognized

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


def long_marked(text: str) -> list[str]:
    """text as an edition that marks long vowels prints it: Wiktionary's macrons kept,
    its breves dropped (such editions leave short vowels plain), and a vowel of disputed
    length (ῡ̆) both ways: λῡ̆́ω → λῡ́ω, λύω; ᾰ̓γᾰθός → ἀγαθός."""
    letters = []  # each letter with its marks, without breves
    disputed = []  # whether the letter has both a macron and a breve
    for char in unicodedata.normalize("NFD", text):
        if unicodedata.combining(char) and letters:
            disputed[-1] = disputed[-1] or (char == BREVE and MACRON in letters[-1])
            disputed[-1] = disputed[-1] or (char == MACRON and BREVE in letters[-1])
            letters[-1] += char
        else:
            letters.append(char)
            disputed.append(False)
    options = [
        [letter.replace(BREVE, ""), letter.replace(BREVE, "").replace(MACRON, "")]
        if both
        else [letter.replace(BREVE, "")]
        for letter, both in zip(letters, disputed)
    ]
    marked = []
    for choice in product(*options):
        marked.append("".join(choice))
        # A long vowel with a breathing or accent has no letter of its own, so its marks
        # come in either order: Wiktionary's macron first (ῑ̓́), or the accented letter
        # with the macron after it (ἴ̄), as polytonic keyboards type it
        marked.append("".join(_macron_last(letter) for letter in choice))
    return list(dict.fromkeys(unicodedata.normalize("NFC", m) for m in marked))


def _macron_last(letter):
    if MACRON not in letter:
        return letter
    return letter.replace(MACRON, "") + MACRON


def lookup_spellings(form: str) -> list[str]:
    """The spellings of form a Greek text prints: without length marks, as most editions
    print it, and with its long vowels marked, as school editions do (λῡ́ουσῐν →
    λύουσιν, λῡ́ουσιν); each with a grave for a final acute. A Kindle folds neither, so
    each is a label, and a marked tap reaches only the forms with those lengths.
    Capitals are added for some entries only (capitalizes). A final σ, which some table
    forms have (ἀγαπήσῃσ), is written ς."""
    spellings = [strip_length(form), *long_marked(form)]
    spellings = [FINAL_SIGMA.sub("ς", spelling) for spelling in spellings]
    return list(dict.fromkeys(s for p in spellings for s in (p, with_grave(p))))


FINAL_SIGMA = re.compile(r"σ$")
# εἰμί's forms that the tables of a perfect's periphrastic optative split off as forms of
# their own ("λελυμένοι εἶεν" gives εἶεν, linked to λελυμένοι): 1,700 verbs had them
AUXILIARY_FORMS = {"εἶτον", "εἶτε", "εἶεν", "εἴτην", "εἶμεν"}


def skips_form(form):
    """Whether a table form is no spelling of its entry: one of εἰμί's, split off a
    periphrastic form (it links to the participle it goes with, not to itself), or one
    with Latin letters, a romanization or a table note ("tēîsĭnĭ", "third declension"), or
    one Kaikki could not tag."""
    if unrecognized(form):
        return True
    word = form.get("form", "")
    links = form.get("links") or []
    split_off = (
        word in AUXILIARY_FORMS
        and bool(links)
        and links[0][0] == word
        and links[0][1].split("#")[0] != word
    )
    return split_off or any(char.isascii() and char.isalpha() for char in word)


# Words that open a sentence or a speech often enough for their capitalized spellings to
# pay for their labels: the article, pronouns, particles, conjunctions, prepositions
CAPITALIZED_POS = {"pron", "det", "conj", "particle", "prep", "adv", "intj", "num"}


def capitalizes(pos, headword):
    """Whether a spelling also gets its capitalized form: every headword, and every form
    of a word in CAPITALIZED_POS. Capitalizing every form doubled the labels for 0.8% of
    corpus tokens (roadmap, Stage 9)."""
    return headword or pos in CAPITALIZED_POS


# The romanization after the headword: "λόγος • (lógos) m (genitive λόγου)"
ROMANIZATION = re.compile(r"^•\s*\([^()]*\)\s*")
# Head lines of these parts of speech name a gender for the masculine they start with
GENDERED_FORMS = {"adj", "participle", "det", "pron", "num"}
# Genders as dictionaries of Greek give them, by the article: λόγος, λόγου, ὁ
GENDERS = {"m": "ὁ", "f": "ἡ", "n": "τό", "or": "or", "sg": "sg.", "pl": "pl."}


def head_line(text, pos):
    """The head line after the headword, without its romanization, and without the
    gender of an adjective's masculine: "• (lógos) m (genitive λόγου); second
    declension" → "m (genitive λόγου); second declension"."""
    text = ROMANIZATION.sub("", text)
    if pos in GENDERED_FORMS:
        text = re.sub(r"^(?:[mfn](?: or [mfn])*)\s*(?=\(|$)", "", text)
    return text


def implied_forms(forms, known):
    return []


# Elision marks: the modifier apostrophe Perseus prints, the quotation mark, the koronis
ELISION_MARKS = "\u02bc\u2019'\u1fbd"
# Before a rough breathing an elided word's last consonant is aspirated: καθʼ for κατά
DEASPIRATE = str.maketrans("θφχ", "τπκ")
ELIDED_VOWELS = ("α", "ε", "ι", "ο", "ά", "έ", "ί", "ό")


def miss_variants(word):
    """(causes, variant) for the spellings a Greek text prints but Wiktionary's forms do
    not: oxia or decomposed accents, length marks Wiktionary does not have, a capital, a
    grave for an acute, the second accent an enclitic puts on the word before it, movable
    nu, elision. A Kindle folds none of them.
    Crasis and dialect forms are not guessed."""
    variants = [((), word)]
    for cause, respell in (
        ("oxia or decomposed", lambda w: [unicodedata.normalize("NFC", w)]),
        # Long vowels marked where Wiktionary marks none, or in another order of marks
        ("length marks", lambda w: [strip_length(w)]),
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
    # The page title: what texts print and form-of links name. The head line is shown,
    # with its length marks, but it is less reliable (ᾱ́ζω for ἄζω, without its breathing)
    headword=lambda header: header.plain_word,
    lookup_spellings=lookup_spellings,
    capitalizes=capitalizes,
    # Accents and breathings belong to the spelling (ὅς, ὡς and ὥς are three words)
    letters=strip_length,
    alternative_tags=frozenset({"alternative"}),
    skips_form=skips_form,
    pos_by_head_template={},
    implied_forms=implied_forms,
    head_line=head_line,
    genders=GENDERS,
    # The languages Greek entries cite most: Modern Greek (6,833 entries), Latin (5,600)
    descendants=("Greek", "Latin", "English"),
    homographs="<i>εἶ</i>, of <i>εἰμί</i> and of <i>εἶμι</i>",
    miss_variants=miss_variants,
)
