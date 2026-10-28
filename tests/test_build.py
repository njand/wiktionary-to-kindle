"""Building the dictionary's XHTML pages from a sorted dump (compiling is stubbed out)."""

import json
from pathlib import Path

from wiktionary_to_kindle import pipeline
from wiktionary_to_kindle.quality.labels import read_entries

from .test_sort_merge import lemma


def run_build(tmp_path, monkeypatch, entries):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline, "compile_mobi", lambda *args: None)
    src = tmp_path / "kaikki-la(sorted).jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    build = pipeline.build_dictionary(str(src), "la", "kindling", ["English"])
    return build, Path(build.files_dir)


def test_entry_without_senses_is_not_indexed(tmp_path, monkeypatch):
    amo = lemma("amo", "verb", "amō", ["to love"])
    # No senses, and a form that is another entry's headword
    empty = lemma("xyzzy", "noun", "xyzzy", [], [("amō", ["nominative", "plural"])])
    build, files = run_build(tmp_path, monkeypatch, [amo, empty])

    entries = read_entries(files)
    assert [e.headword for e in entries] == ["amō"]
    assert len(build.entry_pages) == 1
    assert "xyzzy" not in "".join(p.read_text("utf-8") for p in files.glob("*.xhtml"))


def test_front_page_credits_wiktionary(tmp_path, monkeypatch):
    build, files = run_build(
        tmp_path, monkeypatch, [lemma("amo", "verb", "amō", ["to love"])]
    )
    front = (files / "front.xhtml").read_text("utf-8")
    assert "Wiktionary contributors" in front
    assert "CC BY-SA 4.0" in front
    assert f"Wiktionary data of {build.dump_date}" in front

    opf = (files / "dictionary.opf").read_text("utf-8")
    assert "<dc:rights>CC BY-SA 4.0" in opf
    assert f"<dc:date>{build.build_date}</dc:date>" in opf
    assert opf.index('<itemref idref="front"/>') < opf.index(
        '<itemref idref="page-0"/>'
    )
    assert "$" not in opf


def test_homographs_each_keep_their_spellings(tmp_path, monkeypatch):
    # The popup lists every entry a tap reaches, so no spelling is taken from either
    noun = lemma("latus", "noun", "latus n", ["side"], [("lateris", ["genitive"])])
    adj = lemma("latus", "adj", "lātus", ["wide"], [("lāta", ["feminine"])])
    _build, files = run_build(tmp_path, monkeypatch, [noun, adj])

    entries = read_entries(files)
    assert [(e.headword, e.labels) for e in entries] == [
        ("latus", ["latus", "lateris"]),
        ("lātus", ["lātus", "lāta"]),
    ]
    assert not list(files.glob("card-*.xhtml"))
