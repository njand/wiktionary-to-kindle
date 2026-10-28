"""Lines a lemma keeps for the pages merged into it (diminutives, comparatives, spellings)."""

import json

import pytest

from wiktionary_to_kindle.merge.related import (
    MERGED_KEY,
    merged_page,
    related_lines,
)
from wiktionary_to_kindle.merge.sort import merge_dump
from wiktionary_to_kindle.models.entry import Entry
from wiktionary_to_kindle.render.html_renderer import HTMLRenderer

from .test_sort_merge import find, lemma, pointer


def page(gloss, root, kind="form_of"):
    return {"senses": [{"glosses": [gloss], kind: [{"word": root}]}]}


@pytest.mark.parametrize(
    "gloss, root, kind, meaning",
    [
        (
            "diminutive of flūctus (“wave, billow”): a little wave, wavelet",
            "flūctus",
            "dim.",
            "a little wave, wavelet",
        ),
        ("diminutive of taurus (“bull”)", "taurus", "dim.", ""),
        ("comparative degree of nēquam; worse", "nēquam", "comp.", "worse"),
        ("superlative degree of bonus; best", "bonus", "superl.", "best"),
        ("alternative form of causa", "causa", "alt.", ""),
        ("alternative form of Iapō̆nia: Japan", "Iapō̆nia", "alt.", "Japan"),
        ("Archaic Latin form of Mārs", "Mārs", "archaic", ""),
        ("female equivalent of domitor (“tamer”)", "domitor", "fem.", ""),
        ("abbreviation of opus", "opus", "abbr.", ""),
    ],
)
def test_word_of_its_own_keeps_a_line(gloss, root, kind, meaning):
    assert merged_page(page(gloss, root), "x") == {
        "kind": kind,
        "word": "x",
        "gloss": meaning,
    }


@pytest.mark.parametrize(
    "gloss, root",
    [
        ("genitive singular of fors", "fors"),
        ("inflection of ālus: ; genitive singular", "ālus"),
        ("perfect passive participle of meō", "meō"),
        ("alternative letter-case form of Gallus", "Gallus"),
        ("scribal abbreviation of eōrum", "eōrum"),
    ],
)
def test_forms_of_the_lemma_get_no_line(gloss, root):
    assert merged_page(page(gloss, root), "x") is None


def test_lines_grouped_by_kind_and_header_comparatives_left_out():
    merged = [
        {"kind": "alt.", "word": "caussa", "gloss": ""},
        {"kind": "comp.", "word": "lātior", "gloss": ""},
        {"kind": "dim.", "word": "lātiusculus", "gloss": "rather broad"},
        {"kind": "alt.", "word": "caussa", "gloss": ""},
        {"kind": "alt.", "word": "cāsa", "gloss": "a spelling"},
    ]
    header = "lātus (feminine lāta, comparative lātior, superlative lātissimus)"
    assert related_lines(merged, header) == [
        ("dim.", [("lātiusculus", "rather broad")]),
        ("alt.", [("caussa", ""), ("cāsa", "a spelling")]),
    ]


def test_comparative_with_a_meaning_is_kept():
    merged = [{"kind": "comp.", "word": "nēquior", "gloss": "worse"}]
    assert related_lines(merged, "nēquam (comparative nēquior)") == [
        ("comp.", [("nēquior", "worse")])
    ]


def test_sort_records_merged_pages_on_the_lemma(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = [
        lemma("frigidus", "adj", "frīgidus (feminine frīgida)", ["cold"]),
        pointer(
            "frigidulus",
            "adj",
            "frīgidulus (feminine frīgidula)",
            "diminutive of frīgidus: somewhat cold",
            "frīgidus",
        ),
        pointer(
            "frigidi",
            "adj",
            "frīgidī",
            "genitive singular of frīgidus",
            "frīgidus",
        ),
    ]
    src = tmp_path / "kaikki-la.jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    merged = merge_dump(str(src), "la")
    with open(merged.path, encoding="utf-8") as f:
        frigidus = find([json.loads(line) for line in f], "frigidus", "adj")
    assert frigidus[MERGED_KEY] == [
        {"kind": "dim.", "word": "frīgidulus", "gloss": "somewhat cold"}
    ]

    html = "\n".join(HTMLRenderer.render_entry(Entry(frigidus)))
    assert "<p><i>dim.</i>&#160;<b>frīgidulus</b>: somewhat cold</p>" in html
