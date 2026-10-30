"""The line an entry opens with, written the way Latin dictionaries write it.

Wiktionary's head line labels each form: "rēx m (genitive rēgis, feminine rēgīna); third
declension", "amō (present infinitive amāre, perfect active amāvī, supine amātum); first
conjugation". A dictionary lists the principal parts after the headword without labels
and gives the rest a short one: rēx, rēgis m. · noun, 3rd decl.; fem. rēgīna. A line that
does not have that shape is only shortened (compact_grammar).
"""

import re

ORDINALS = {
    "first": "1st",
    "second": "2nd",
    "third": "3rd",
    "fourth": "4th",
    "fifth": "5th",
}
ORDINAL_PATTERN = re.compile(r"\b(" + "|".join(ORDINALS) + r")\b")

# Labels of the forms a dictionary lists after the headword, by part of speech
# Turkish adds its own: a verb's aorist (gitmek, gider) and a noun's accusative (ev, evi),
# which show the stem suffixes go on
VERB_PARTS = (
    "present infinitive",
    "perfect active",
    "supine",
    "third-person singular simple present",
)
ADJECTIVE_PARTS = ("genitive", "feminine", "neuter", "masculine")
NOUN_PARTS = ("genitive", "definite accusative")
ADJECTIVES = {"adj", "participle", "det", "pron", "num", "gerund"}
# Labels of the other forms, shortened
OTHER_FORMS = {
    "future active participle": "fut. act. part.",
    "comparative": "comp.",
    "superlative": "superl.",
    "adverb": "adv.",
    "feminine": "fem.",
    "masculine": "masc.",
    "neuter": "neut.",
    "accusative": "acc.",
    "ablative": "abl.",
    "plural": "pl.",
    "genitive": "gen.",
    "oblique": "obl.",
}
# Kaikki's part-of-speech codes as the headword line spells them
POS_NAMES = {
    "adj": "adjective",
    "adv": "adverb",
    "prep": "preposition",
    "postp": "postposition",
    "prep_phrase": "prepositional phrase",
    "conj": "conjunction",
    "det": "determiner",
    "pron": "pronoun",
    "num": "numeral",
    "intj": "interjection",
    "name": "proper noun",
}
CASES = {
    "nominative": "nom.",
    "genitive": "gen.",
    "dative": "dat.",
    "accusative": "acc.",
    "ablative": "abl.",
    "vocative": "voc.",
    "locative": "loc.",
}
CASE_PATTERN = re.compile(r"\b(" + "|".join(CASES) + r")\b")
GENDERS = {"m": "m.", "f": "f.", "n": "n.", "c": "c.", "sg": "sg.", "pl": "pl."}


def compact_grammar(remainder, pos):
    """The headword line's grammar, shorter: "third declension" as "3rd decl.", and a
    closing part of speech the line names anyway left out
    ("first/second-declension participle" → "1st/2nd decl.")."""
    text = ORDINAL_PATTERN.sub(lambda m: ORDINALS[m.group(1)], remainder)
    text = re.sub(r"[- ]declension\b", " decl.", text)
    text = re.sub(r" conjugation\b", " conj.", text)
    text = CASE_PATTERN.sub(lambda m: CASES[m.group(1)], text)
    for name in {pos, POS_NAMES.get(pos)} - {None}:
        if text.endswith(" " + name):
            text = text[: -len(name) - 1]
    return text.strip()


def headline(remainder, pos, genders=GENDERS):
    """(forms, gender, grammar, others) for the text after the headword, as markup:
    ", amāre, amāvī, amātum", "<i>m.</i>", "1st conj.", "<i>fem.</i> rēgīna". None when
    the line does not have the usual shape."""
    match = re.fullmatch(
        r"([^()<>;]*?)\s*(?:\(([^()<>]*)\))?\s*;?\s*([^()<>]*)", remainder
    )
    if not match:
        return None
    before, inside, after = match.groups()
    gender = " ".join(genders.get(token, token) for token in before.split())

    if pos == "verb":
        principal = VERB_PARTS
    elif pos in ADJECTIVES:
        principal = ADJECTIVE_PARTS
    else:
        principal = NOUN_PARTS
    forms, others, notes = [], [], []
    for part in inside.split(", ") if inside else []:
        label = next(
            (lb for lb in (*principal, *OTHER_FORMS) if part.startswith(lb + " ")),
            None,
        )
        if label in principal:
            forms.append(part[len(label) + 1 :])
        elif label:
            others.append(f"<i>{OTHER_FORMS[label]}</i> {part[len(label) + 1 :]}")
        else:
            # "not comparable", "indeclinable", "+ ablative"
            notes.append(CASE_PATTERN.sub(lambda m: CASES[m.group(1)], part))
    grammar = ", ".join(filter(None, [compact_grammar(after, pos), *notes]))
    return (
        "".join(f", {form}" for form in forms),
        f"<i>{gender}</i>" if gender else "",
        grammar,
        ", ".join(others),
    )


def headline_tail(header, pos, language):
    """Markup for what follows the headword on its line: the principal parts, gender,
    then part of speech and class in italics, and the other forms on a smaller line."""
    shown = POS_NAMES.get(pos, pos)
    parts = None
    if header.labelled is not None and "<br/>" not in header.remainder:
        labelled = language.head_line(header.labelled, pos)
        parts = headline(labelled, pos, language.genders)
    if parts is None:
        grammar = compact_grammar(language.head_line(header.remainder or "", pos), pos)
        return (f" {grammar}" if grammar else "") + (
            f" &#183; <i>{shown}</i>" if shown else ""
        )
    forms, gender, grammar, others = parts
    tail = forms + (f" {gender}" if gender else "")
    kind = ", ".join(filter(None, [shown, grammar]))
    if kind:
        tail += f" &#183; <i>{kind}</i>"
    if others:
        tail += f'<br/><font size="-1">{others}</font>'
    return tail
