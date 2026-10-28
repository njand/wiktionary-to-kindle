"""Merge of form-of / alt-of entries into their lemmas during sort_jsonl.

Fixtures mirror the shape of real Kaikki Latin entries (lātior, amātus, caussa, ...).
"""

import json

import pytest

from wiktionary_to_kindle.builders.kindle_dict import KindleDict
from wiktionary_to_kindle.models.entry import Entry
from wiktionary_to_kindle.utils import form_of_root


def lemma(word, pos, expansion, glosses, forms=()):
    return {
        "word": word,
        "pos": pos,
        "lang_code": "la",
        "head_templates": [{"name": f"la-{pos}", "expansion": expansion}],
        "forms": [{"form": f, "tags": tags} for f, tags in forms],
        "senses": [{"glosses": [g]} for g in glosses],
    }


def pointer(word, pos, expansion, gloss, root, kind="form_of", forms=()):
    entry = lemma(word, pos, expansion, [], forms)
    entry["senses"] = [{"glosses": [gloss], kind: [{"word": root}]}]
    return entry


ENTRIES = [
    lemma(
        "amo",
        "verb",
        "amō (present infinitive amāre); first conjugation",
        ["to love"],
        [("amābō", ["first-person", "singular", "future"])],
    ),
    pointer(
        "amabo",
        "verb",
        "amābō",
        "first-person singular future active indicative of amō",
        "amō",
        forms=[("amābō", ["canonical"])],
    ),
    # Participle with its own meaning: Kaikki marks it form_of amō, but it defines a word
    pointer(
        "amatus",
        "verb",
        "amātus (feminine amāta, neuter amātum); participle",
        "loved; having been loved",
        "amō",
        forms=[("amātam", ["accusative", "feminine", "singular"])],
    ),
    lemma("latus", "adj", "lātus (feminine lāta, neuter lātum)", ["wide, broad"]),
    lemma("latus", "noun", "latus n (genitive lateris)", ["side, flank"]),
    pointer("latus", "verb", "lātus (feminine lāta)", "borne, carried", "ferō"),
    pointer(
        "latior",
        "adj",
        "lātior (comparative, neuter lātius)",
        "comparative degree of lātus",
        "lātus",
        forms=[("lātiōrem", ["accusative", "singular"])],
    ),
    lemma("causa", "noun", "causa f (genitive causae)", ["cause, reason"]),
    pointer(
        "caussa",
        "noun",
        "caussa f (genitive caussae)",
        "alternative form of causa",
        "causa",
        kind="alt_of",
        forms=[("caussārum", ["genitive", "plural"])],
    ),
    # Chain: a form of an alternative form
    pointer(
        "caussis",
        "noun",
        "caussīs",
        "dative/ablative plural of caussa",
        "caussa",
        forms=[("caussīs", ["canonical"])],
    ),
    # Orphan: its lemma (fors) is not in the dump
    pointer("fortis", "noun", "fortis", "genitive singular of fors", "fors"),
]


@pytest.fixture
def sorted_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "kaikki-la.jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in ENTRIES),
        encoding="utf-8",
    )
    kd = KindleDict(str(src), "la", "kindlegen")
    kd.sort_jsonl()
    with open(kd.wiktionary_fp, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def find(entries, word, pos):
    matches = [e for e in entries if e["word"] == word and e["pos"] == pos]
    assert len(matches) == 1, f"expected one {word} ({pos}), got {len(matches)}"
    return matches[0]


def forms_of(entry):
    return {f["form"] for f in entry.get("forms", [])}


def test_comparative_merges_into_macronized_lemma(sorted_entries):
    assert "lātiōrem" in forms_of(find(sorted_entries, "latus", "adj"))
    assert "lātiōrem" not in forms_of(find(sorted_entries, "latus", "noun"))
    assert "lātiōrem" not in forms_of(find(sorted_entries, "latus", "verb"))
    assert all(e["word"] != "latior" for e in sorted_entries)


def test_form_of_entry_merges_with_its_parse(sorted_entries):
    amo = find(sorted_entries, "amo", "verb")
    assert "amābō" in forms_of(amo)
    assert all(e["word"] != "amabo" for e in sorted_entries)


def test_participle_with_own_meaning_is_kept(sorted_entries):
    amatus = find(sorted_entries, "amatus", "verb")
    assert "amātam" in forms_of(amatus)
    assert "amātam" not in forms_of(find(sorted_entries, "amo", "verb"))
    glosses = [b.senses for b in Entry(amatus).senses_blocks]
    assert "loved; having been loved" in glosses[0]


def test_alternative_form_chain_merges(sorted_entries):
    causa = forms_of(find(sorted_entries, "causa", "noun"))
    assert {"caussārum", "caussīs"} <= causa
    assert all(e["word"] not in ("caussa", "caussis") for e in sorted_entries)


def test_orphan_is_kept_with_its_gloss(sorted_entries):
    fortis = find(sorted_entries, "fortis", "noun")
    senses = Entry(fortis).senses_blocks[0].senses
    assert "genitive singular of fors" in senses


def test_sorted_file_is_cached_until_input_changes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "kaikki-la.jsonl"
    src.write_text(json.dumps(ENTRIES[0], ensure_ascii=False) + "\n", encoding="utf-8")

    def sort(**kwargs):
        kd = KindleDict(str(src), "la", "kindlegen")
        kd.sort_jsonl(**kwargs)
        return kd.line_count  # only set when a sort actually ran

    assert sort() == 1
    assert sort() is None
    assert sort(force=True) == 1

    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in ENTRIES[:2]),
        encoding="utf-8",
    )
    assert sort() == 1  # input changed: sorted again (amābō merges into amō)


@pytest.mark.parametrize(
    "sense, expected",
    [
        (
            {"glosses": ["genitive singular of fors"], "form_of": [{"word": "fors"}]},
            "fors",
        ),
        (
            {"glosses": ["alternative form of causa"], "alt_of": [{"word": "causa"}]},
            "causa",
        ),
        ({"glosses": ["inflection of amō:"], "form_of": [{"word": "amō"}]}, "amō"),
        ({"glosses": ["loved; having been loved"], "form_of": [{"word": "amō"}]}, None),
        ({"glosses": ["wide, broad"]}, None),
    ],
)
def test_form_of_root(sense, expected):
    assert form_of_root(sense) == expected
