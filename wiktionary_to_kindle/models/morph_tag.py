from collections import Counter
from typing import ClassVar


class MorphTag:
    GENDERS = ("masculine", "feminine", "neuter")
    CASES = (
        "nominative",
        "accusative",
        "genitive",
        "dative",
        "ablative",
        "vocative",
        "locative",
        "oblique",
    )
    NUMBERS = ("singular", "plural")
    DEGREES = ("comparative", "superlative")
    PERSONS = ("first-person", "second-person", "third-person")
    TENSES = (
        "present",
        "imperfect",
        "future",
        "perfect",
        "pluperfect",
        "aorist",
        "preterite",
    )
    MOODS = ("indicative", "subjunctive", "imperative", "conditional")
    VOICES = ("active", "passive")
    VERBAL_FORMS = ("infinitive", "participle", "supine", "gerund")
    MISC_FORMS = (
        "sigmatic",
        "adverb",
        "possessive",
        "diminutive",
        "romanization",
        "sometimes",
    )

    NOUN_ADJ_ORDER = GENDERS + CASES + NUMBERS + DEGREES
    DEFAULT_ORDER = (
        PERSONS + NUMBERS + TENSES + MOODS + VOICES + VERBAL_FORMS + MISC_FORMS
    )

    ABBREVIATIONS: ClassVar[dict[str, str]] = {
        "masculine": "m",
        "feminine": "f",
        "neuter": "n",
        "nominative": "nom",
        "accusative": "acc",
        "genitive": "gen",
        "dative": "dat",
        "ablative": "abl",
        "vocative": "voc",
        "locative": "loc",
        "oblique": "obl",
        "singular": "sg",
        "plural": "pl",
        "first-person": "1",
        "second-person": "2",
        "third-person": "3",
        "active": "act",
        "passive": "pass",
        "indicative": "ind",
        "subjunctive": "subj",
        "imperative": "imp",
        "conditional": "cond",
        "present": "pres",
        "imperfect": "impf",
        "future": "fut",
        "perfect": "perf",
        "pluperfect": "plup",
        "aorist": "aor",
        "preterite": "pret",
        "infinitive": "inf",
        "participle": "part",
        "supine": "sup",
        "gerund": "ger",
        "comparative": "comp",
        "superlative": "superl",
        "adverb": "adv",
        "possessive": "poss",
        "diminutive": "dim",
        "romanization": "rom",
        "sometimes": "smt",
        "sigmatic": "sig",
    }

    ABBREVIATED_ORDER = (
        "sg",
        "pl",
        "nom",
        "gen",
        "dat",
        "acc",
        "abl",
        "voc",
        "loc",
        "obl",
        "ind",
        "subj",
        "imp",
        "cond",
        "act",
        "pass",
        "pres",
        "impf",
        "fut",
        "perf",
        "plup",
        "aor",
        "pret",
        "1sg",
        "2sg",
        "3sg",
        "1pl",
        "2pl",
        "3pl",
        "inf",
        "part",
        "sup",
        "ger",
        "comp",
        "superl",
        "adv",
        "poss",
        "dim",
        "m",
        "f",
        "n",
        "rom",
        "smt",
        "sig",
    )

    CLASS_ABBREVIATIONS: ClassVar[dict[str, frozenset[str]]] = {
        "GENDER": frozenset({"m", "f", "n"}),
        "CASE": frozenset({"nom", "gen", "dat", "acc", "abl", "voc", "loc", "obl"}),
        "NUMBER": frozenset({"sg", "pl"}),
        "DEGREE": frozenset({"comp", "superl"}),
        "MOOD": frozenset({"ind", "subj", "imp", "cond"}),
        "VOICE": frozenset({"act", "pass"}),
        "TENSE": frozenset({"pres", "impf", "fut", "perf", "plup", "aor", "pret"}),
        "PERSON": frozenset({"1sg", "2sg", "3sg", "1pl", "2pl", "3pl"}),
        "VERBAL_FORM": frozenset({"inf", "part", "sup", "ger"}),
        "MISC_FORM": frozenset({"adv", "poss", "dim", "rom", "smt", "sig"}),
    }

    ABBREVIATED_CLASS: ClassVar[dict[str, str]] = {
        ab: c for c, abvs in CLASS_ABBREVIATIONS.items() for ab in abvs
    }

    def __init__(self, tags):
        self.tags = tags
        self.abbreviated_tags = self.abbreviate()

    def is_subset(self, other):
        return len(self.tags & other.tags) == len(self)

    def abbreviate(self):
        sorted_tags = sorted(
            self.tags,
            key=lambda tag: (
                self.__class__.NOUN_ADJ_ORDER.index(tag)
                if tag in self.__class__.NOUN_ADJ_ORDER
                else float("inf"),
                self.__class__.DEFAULT_ORDER.index(tag)
                if tag in self.__class__.DEFAULT_ORDER
                else float("inf"),
            ),
        )

        filtered_tags = set()
        abbreviated_tags = []
        for tag in sorted_tags:
            if tag in self.__class__.ABBREVIATIONS:
                filtered_tags.add(tag)
                abbreviated_tags.append(self.__class__.ABBREVIATIONS[tag])
        self.tags = filtered_tags

        for person in ["1", "2", "3"]:
            for number in ["sg", "pl"]:
                if person in abbreviated_tags and number in abbreviated_tags:
                    abbreviated_tags.remove(person)
                    abbreviated_tags.remove(number)
                    abbreviated_tags.insert(0, person + number)

        return abbreviated_tags

    def combine(self, other):
        diffs = self.tags.symmetric_difference(other.tags)

        class_diffs = Counter()
        for tag in diffs:
            abbr = self.__class__.ABBREVIATIONS.get(tag)
            abbr_class = self.__class__.ABBREVIATED_CLASS.get(abbr)
            class_diffs[abbr_class] += 1

        if len(class_diffs) == 1:
            combined_tags = self.tags.union(other.tags)
            return [MorphTag(combined_tags)]

        return [self, other]

    def __str__(self):
        if len(self.abbreviated_tags) == 0:
            return ""

        tag_list = []
        for i, tag in enumerate(self.abbreviated_tags):
            tag_list.append(tag)
            if i + 1 < len(self.abbreviated_tags):
                next_tag = self.abbreviated_tags[i + 1]
                if self.__class__.ABBREVIATED_CLASS.get(
                    tag
                ) == self.__class__.ABBREVIATED_CLASS.get(next_tag):
                    tag_list.append("/")
                else:
                    tag_list.append(".")
            else:
                tag_list.append(".")

        return "".join(tag_list)

    def __len__(self):
        return len(self.tags)

    def sort_key(self):
        """Order by the first abbreviation in ABBREVIATED_ORDER that only one tag has; the
        tag that has it comes first."""
        return tuple(abb not in self.abbreviated_tags for abb in self.ABBREVIATED_ORDER)

    def __lt__(self, other):
        return self.sort_key() < other.sort_key()
