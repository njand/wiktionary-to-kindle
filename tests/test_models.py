"""Parsing of Kaikki entries into the model classes."""

import pytest

from wiktionary_to_kindle.models.header import Header


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
