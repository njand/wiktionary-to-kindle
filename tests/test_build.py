"""Building the dictionary's XHTML pages from a sorted dump (compiling is stubbed out)."""

import json
from pathlib import Path

from wiktionary_to_kindle.builders.kindle_dict import KindleDict
from wiktionary_to_kindle.quality.labels import read_entries

from .test_sort_merge import lemma


def build(tmp_path, monkeypatch, entries):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(KindleDict, "make_mobi", lambda self: None)
    src = tmp_path / "kaikki-la(sorted).jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    kd = KindleDict(str(src), "la", "kindling")
    kd.build_dictionary(descendant_langs=["English"])
    return kd, Path(kd.output_sub_dir)


def test_entry_without_senses_is_not_indexed(tmp_path, monkeypatch):
    amo = lemma("amo", "verb", "amō", ["to love"])
    # No senses, and a form that is another entry's headword (would get a card)
    empty = lemma("xyzzy", "noun", "xyzzy", [], [("amō", ["nominative", "plural"])])
    kd, files = build(tmp_path, monkeypatch, [amo, empty])

    entries = read_entries(files)
    assert [e.headword for e in entries] == ["amō"]  # no card for xyzzy's form amō
    assert "xyzzy" not in kd.entries
    assert "xyzzy" not in "".join(p.read_text("utf-8") for p in files.glob("*.xhtml"))


def test_front_page_credits_wiktionary(tmp_path, monkeypatch):
    kd, files = build(tmp_path, monkeypatch, [lemma("amo", "verb", "amō", ["to love"])])
    front = (files / "front.xhtml").read_text("utf-8")
    assert "Wiktionary contributors" in front
    assert "CC BY-SA 4.0" in front
    assert f"Wiktionary data of {kd.dump_date}" in front

    opf = (files / "dictionary.opf").read_text("utf-8")
    assert "<dc:rights>CC BY-SA 4.0" in opf
    assert f"<dc:date>{kd.build_date}</dc:date>" in opf
    assert opf.index('<itemref idref="front"/>') < opf.index(
        '<itemref idref="page-0"/>'
    )
    assert "$" not in opf
