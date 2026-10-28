"""Parsing of Kaikki entries into the model classes."""

import pytest

from wiktionary_to_kindle.models.header import Header
from wiktionary_to_kindle.models.inflection import Inflection
from wiktionary_to_kindle.models.morph_tag import MorphTag


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
