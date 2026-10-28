"""Each spelling gets one owner: an entry, or a disambiguation card for ambiguous ones."""

import json
import re
from pathlib import Path

import pytest

from wiktionary_to_kindle.builders.kindle_dict import KindleDict
from wiktionary_to_kindle.builders.label_resolver import LabelResolver
from wiktionary_to_kindle.quality import coverage
from wiktionary_to_kindle.quality.labels import build_index, read_entries

from .test_sort_merge import ENTRIES, lemma


def resolve(*entries):
    """entries: (headword, labels) or (headword, labels, size, pos)."""
    resolver = LabelResolver()
    for entry_id, entry in enumerate(entries, 1):
        resolver.add(entry_id, *entry)
    resolver.resolve()
    return resolver


def card_for(resolver, label):
    (card,) = [card for card in resolver.cards if label in card.labels]
    return card


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

    assert card_for(resolver, "latus").owners == [1, 2, 3]
    # Two entries share the macronized spelling, so it gets a card of its own
    assert card_for(resolver, "lātus").owners == [2, 3]
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
    assert resolver.entry_labels(1, "lātus", ["lātus", "lātum"]) == ("lātus", ["lātum"])


def test_card_lists_larger_entries_first_and_names_last():
    # est: edō "eat" and sum "be"; Wiktionary's sum entry is much longer
    resolver = resolve(
        ("edō", ["est", "ēst"], 9_000, "verb"),
        ("Est", [], 90_000, "name"),
        ("sum", ["est"], 60_000, "verb"),
    )
    assert card_for(resolver, "est").owners == [3, 1, 2]


def test_card_takes_every_case_spelling():
    resolver = resolve(("amor", []), ("Amor", []))
    (card,) = resolver.cards
    assert card.labels == ["amor", "Amor"]
    assert card.reached == {1: ["amor"], 2: ["Amor"]}


def test_ligature_spellings_share_a_card():
    resolver = resolve(("Aegyptus", ["Aegyptī"]), ("aegyptus", ["aegyptī"]))
    card = card_for(resolver, "aegypti")
    # A text writing Ægypti matches a card label ignoring case, not by index order
    assert {"Aegypti", "Ægypti", "ægypti"} <= set(card.labels)
    assert card.labels[0] == "aegypti"


def test_punctuation_alone_makes_no_card():
    # The device ignores the dots, but a tap on "ad" matches ad's label exactly
    resolver = resolve(("ad", []), ("a.d.", ["A.D."]))
    assert resolver.cards == []


def test_sole_owner_of_a_spelling_gets_it_unmacronized():
    # A tap on "non" reaches nōn and Non.; only nōn is spelled n-o-n
    resolver = resolve(("nōn", []), ("Non.", []))
    assert resolver.cards == []
    assert resolver.entry_labels(1, "nōn", ["nōn"]) == ("nōn", ["non"])
    assert resolver.entry_labels(2, "Non.", ["Non."]) == ("Non.", [])


def test_bare_spelling_card_when_every_label_has_punctuation():
    resolver = resolve(("M.", []), ("M'", []))
    card = card_for(resolver, "M")
    assert sorted(card.owners) == [1, 2]
    assert card.reached == {1: ["M."], 2: ["M'"]}


def test_card_reaches_owners_by_their_own_spellings():
    # The card's label "latum" is no entry's label; each row shows its own form's parse
    resolver = resolve(("lātus", ["lātum"]), ("ferō", ["lātum", "lătum"]))
    card = card_for(resolver, "latum")
    assert card.reached == {1: ["lātum"], 2: ["lātum", "lătum"]}


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
    # The three homographs are numbered by their place on the latus card
    orths = re.findall(r'<idx:orth value="(l[aā]tus[¹²³]?)">', pages)
    assert len(set(orths)) == 3
    assert all(orth[-1] in "¹²³" for orth in orths)
    assert '<idx:iform value="lātum" exact="yes" />' in pages  # only ferō has it


def test_cards_differing_by_u_or_j_spelling_merge():
    # Both entries have cōnservandī, and so its u spelling from lookup_spellings
    forms = ["cōnservandī", "cōnseruandī"]
    resolver = resolve(("cōnservō", forms), ("cōnservandus", forms))
    (card,) = resolver.cards
    # Headed by Wiktionary's spelling
    assert card.labels == ["conservandi", "cōnservandī", "conseruandi", "cōnseruandī"]
    assert card.id_number == 1
    assert resolver.entry_labels(1, "cōnservō", ["cōnservō", *forms]) == (
        "cōnservō",
        [],
    )


def test_card_takes_no_spelling_of_another_fold():
    # aͣ weighs as a plus a mark: its card must not take "a", which ab and ā share
    resolver = resolve(("anima", ["aͣ"]), ("aliquis", ["aͣ"]), ("ab", ["a"]), ("ā", []))
    assert card_for(resolver, "aͣ").owners == [1, 2]
    assert sorted(card_for(resolver, "a").owners) == [3, 4]
