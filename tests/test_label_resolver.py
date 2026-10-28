"""Each spelling gets one owner: an entry, or a disambiguation card for ambiguous ones."""

import json
from pathlib import Path

import pytest

from wiktionary_to_kindle.builders.kindle_dict import KindleDict
from wiktionary_to_kindle.builders.label_resolver import LabelResolver
from wiktionary_to_kindle.quality import coverage
from wiktionary_to_kindle.quality.labels import build_index, read_entries

from .test_sort_merge import ENTRIES, lemma


def resolve(*entries):
    resolver = LabelResolver()
    for entry_id, (head, labels) in enumerate(entries, 1):
        resolver.add(entry_id, head, labels)
    resolver.resolve()
    return resolver


def test_unique_spellings_stay_on_their_entries():
    resolver = resolve(("amō", ["amāre", "amābō"]), ("puella", ["puellae"]))
    assert resolver.cards == []
    assert resolver.entry_labels(1, "amō", ["amō", "amāre", "amābō"]) == (
        "amō",
        ["amāre", "amābō"],
    )


def test_ambiguous_key_gets_card_for_unmacronized_spelling():
    # latus "side", lātus "wide", lātus "carried"
    resolver = resolve(("latus", ["lateris"]), ("lātus", ["lāta"]), ("lātus", []))
    by_label = {label: card for card in resolver.cards for label in card.labels}

    assert by_label["latus"].owners == [1, 2, 3]
    # Two entries share the macronized spelling, so it gets a card of its own
    assert by_label["lātus"].owners == [2, 3]
    assert resolver.entry_labels(1, "latus", ["latus", "lateris"]) == (
        "latus¹",
        ["lateris"],
    )
    assert resolver.entry_labels(3, "lātus", ["lātus"]) == ("lātus²", [])


def test_macronized_spelling_with_one_owner_stays():
    # Unmacronized "latum" reaches both; "lātum" belongs to one
    resolver = resolve(("lātus", ["lātum"]), ("latum", []))
    (card,) = resolver.cards
    assert card.labels == ["latum"]
    assert card.owners == [2, 1]  # the entry whose headword is "latum" first
    assert resolver.entry_labels(1, "lātus", ["lātus", "lātum"]) == ("lātus", ["lātum"])


def test_card_takes_every_case_spelling():
    resolver = resolve(("amor", []), ("Amor", []))
    (card,) = resolver.cards
    assert card.labels == ["amor", "Amor"]
    assert card.reached == {1: ["amor"], 2: ["Amor"]}


def test_ligature_spellings_share_a_card():
    resolver = resolve(("caelum", []), ("cælum", []))
    (card,) = resolver.cards
    assert set(card.labels) == {"caelum", "cælum"}


@pytest.fixture
def built(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(KindleDict, "make_mobi", lambda self: None)
    entries = ENTRIES + [
        lemma(
            "fero",
            "verb",
            "ferō (present infinitive ferre, supine lātum)",
            ["to carry"],
            [("lātum", ["supine"]), ("sublātum", ["supine"])],
        ),
        # Shares the exact spelling sublātum with ferō's (made-up) supine
        lemma("sublatus", "adj", "sublātus", ["lofty"], [("sublātum", ["neuter"])]),
    ]
    src = tmp_path / "kaikki-la.jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    kd = KindleDict(str(src), "la", "kindling")
    kd.sort_jsonl()
    kd.build_dictionary(descendant_langs=["English"])
    return Path(kd.output_sub_dir)


@pytest.mark.parametrize(
    "word", ["latus", "Latus", "LATUS", "lātus", "Lātus", "latum", "lātum", "amo"]
)
def test_built_dictionary_has_no_ambiguous_taps(built, word):
    index = build_index(read_entries(built))
    outcome, _run = coverage.resolve(index, word)
    assert outcome in ("unique", "spelling")


def test_built_cards_link_and_parse(built):
    cards = "".join(p.read_text("utf-8") for p in built.glob("card-*.xhtml"))
    assert '<idx:orth value="latus">' in cards
    assert '<idx:orth value="lātus">' in cards
    sublatum = cards[cards.index('value="sublātum"') :]
    # Both entries listed, each with the parse of its sublātum
    assert (
        'ferō</b></a> <span class="pos">verb</span> <span class="tag">sup.</span>'
        in sublatum
    )
    assert '<span class="tag">n.</span>: lofty' in sublatum
    assert 'href="0000.xhtml#' in cards

    pages = "".join(p.read_text("utf-8") for p in built.glob("0*.xhtml"))
    assert '<idx:orth value="latus¹">' in pages
    assert '<idx:iform value="lātum" exact="yes" />' in pages  # only ferō has it
