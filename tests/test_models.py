"""Parsing of Kaikki entries into the model classes."""

import pytest

from wiktionary_to_kindle.models.entry import Entry
from wiktionary_to_kindle.models.header import Header
from wiktionary_to_kindle.models.inflection import Inflection
from wiktionary_to_kindle.models.morph_tag import MorphTag
from wiktionary_to_kindle.utils import (
    generate_vowel_variants,
    kindle_fold,
    lookup_spellings,
    sanitize_xhtml,
)


@pytest.mark.parametrize(
    "plain, expansion, prefix, head_word, remainder",
    [
        ("dico", "dīcō (present infinitive dīcere)", "", "dīcō", "(dīcere)"),
        ("mater", "mā̆ter f", "", "mā̆ter", "f"),
        ("amatus", "ā̆mā̆tus (feminine ā̆mā̆ta)", "", "ā̆mā̆tus", "(ā̆mā̆ta)"),
        # The breves of the first letters push the end past more ā̆ vowels
        ("aeios", "ā̆ē̆ī̆ō̆s m", "", "ā̆ē̆ī̆ō̆s", "m"),
        ("aeio", "ā̆ē̆ī̆ō̆", "", "ā̆ē̆ī̆ō̆", ""),
        # Combining marks before the headword must not shift it
        ("amatus", "(ā̆) ā̆mā̆tus x", "(ā̆) ", "ā̆mā̆tus", "x"),
        ("amo", "something else", "", "amo", "something else"),
    ],
)
def test_header_split(plain, expansion, prefix, head_word, remainder):
    header = Header(plain, expansion)
    assert (header.prefix, header.head_word, header.remainder) == (
        prefix,
        head_word,
        remainder,
    )


def test_superlative_and_supine_abbreviate_differently():
    superlative = MorphTag({"nominative", "superlative"})
    supine = MorphTag({"supine"})
    assert str(superlative) == "nom.superl."
    assert str(supine) == "sup."
    # Tags differing in one class merge; superlative (degree) and supine (verbal form) do not
    assert len(superlative.combine(MorphTag({"nominative", "comparative"}))) == 1
    assert len(supine.combine(MorphTag({"infinitive"}))) == 1
    assert len(MorphTag({"superlative"}).combine(supine)) == 2


def test_morph_tag_ordering_is_boolean():
    nom = MorphTag({"nominative", "singular"})
    gen = MorphTag({"genitive", "singular"})
    assert nom < gen
    assert not gen < nom
    assert (nom < MorphTag({"nominative", "singular"})) is False


def test_inflections_sort_with_and_without_tags():
    untagged = Inflection("b", None)
    genitive = Inflection("a", None)
    genitive.add_tags({"genitive", "singular"})
    nominative = Inflection("c", None)
    nominative.add_tags({"nominative", "singular"})
    assert sorted([nominative, genitive, untagged]) == [untagged, nominative, genitive]


def test_entry_leaves_glosses_alone():
    raw_glosses = ["to love", "to be fond of"]
    entry = Entry(
        {
            "word": "amo",
            "pos": "verb",
            "senses": [{"glosses": list(raw_glosses), "raw_glosses": raw_glosses}],
        }
    )
    assert raw_glosses == ["to love", "to be fond of"]
    sense = entry.senses_blocks[0].senses["to love"]
    assert "to be fond of" in sense.sub_glosses.senses


@pytest.mark.parametrize(
    "text, expected",
    [
        ("a & b", "a &amp; b"),
        ("&amp; &#257; &#x101; &lt;", "&amp; &#257; &#x101; &lt;"),
        ("&nbsp; AT&T;", "&amp;nbsp; AT&amp;T;"),  # not defined in XML
        ("x < y <br/> <i>z</i>", "x &lt; y <br/> <i>z</i>"),
    ],
)
def test_sanitize_xhtml(text, expected):
    assert sanitize_xhtml(text) == expected


def test_vowel_variants_resolve_disputed_length():
    variants = generate_vowel_variants("Ā̆mā̆tus")
    assert sorted(variants) == sorted(["Amatus", "Āmatus", "Amātus", "Āmātus"])
    assert all(len(v) == len("amatus") for v in variants)  # precomposed ā


@pytest.mark.parametrize(
    "form, spellings",
    [
        ("puella", ["puella"]),
        # u for consonantal v
        ("vir", ["vir", "uir"]),
        ("Vīvō", ["Vīvō", "Uīuō"]),
        # j for consonantal i: at the start, between vowels, after a prefix
        ("iam", ["iam", "jam"]),
        ("Iūlius", ["Iūlius", "Jūlius"]),
        ("cuius", ["cuius", "cujus"]),
        ("maior", ["maior", "major"]),
        ("adiuvō", ["adiuvō", "adiuuō", "adjuvō"]),
        ("iniūria", ["iniūria", "injūria"]),
        # Vowels, not consonants
        ("quia", ["quia"]),
        ("iī", ["iī"]),
        ("fīlius", ["fīlius"]),
        # A tie bar weighs as itself, so the plain spelling is added
        ("Orphe͡us", ["Orphe͡us", "Orpheus"]),
    ],
)
def test_lookup_spellings(form, spellings):
    assert lookup_spellings(form) == spellings


def test_lookup_spellings_reach_plain_taps():
    assert kindle_fold("Orpheus") in map(kindle_fold, lookup_spellings("Orphe͡us"))
    assert "uir" in map(kindle_fold, lookup_spellings("vir"))


def test_entry_is_found_by_u_and_j_spellings():
    entry = Entry(
        {
            "word": "iuvenis",
            "pos": "noun",
            "head_templates": [{"name": "la-noun", "expansion": "iuvenis m"}],
            "forms": [{"form": "iuvenem", "tags": ["accusative", "singular"]}],
            "senses": [{"glosses": ["young man"]}],
        }
    )
    assert {"iuuenis", "juvenis", "iuuenem", "juvenem"} <= entry.all_forms
