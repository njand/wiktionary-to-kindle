import struct

import pytest

from wiktionary_to_kindle.stardict import Bundle, _records, unaccented


@pytest.mark.parametrize(
    "word, expected",
    [
        ("amāvistī", "amavisti"),
        ("Rōmānī", "Romani"),
        ("ā̆b", "ab"),  # the separate breve goes too
        ("Orphe͡us", "Orpheus"),
        ("n̄", "n̄"),  # abbreviation signs stay
        ("aͣ", "aͣ"),
        ("cæna", "cæna"),
        ("lātus²", "latus²"),
    ],
)
def test_unaccented(word, expected):
    assert unaccented(word) == expected


def write_bundle(path, articles, synonyms):
    """A bundle as kindling writes it: words in .idx order with their articles."""
    path.mkdir()
    stem = path / path.name
    idx, data = bytearray(), bytearray()
    for word, article in articles:
        raw = article.encode("utf-8")
        idx += word.encode("utf-8") + b"\0" + struct.pack(">II", len(data), len(raw))
        data += raw
    syn = b"".join(
        w.encode("utf-8") + b"\0" + struct.pack(">I", i) for w, i in synonyms
    )
    stem.with_suffix(".idx").write_bytes(idx)
    stem.with_suffix(".dict").write_bytes(data)
    stem.with_suffix(".syn").write_bytes(syn)
    stem.with_suffix(".ifo").write_text(
        "StarDict's dict ifo file\nversion=2.4.2\nbookname=Test\n"
        f"wordcount={len(articles)}\nsynwordcount={len(synonyms)}\n"
        f"idxfilesize={len(idx)}\nsametypesequence=h\n",
        encoding="utf-8",
    )


def test_bundle_relinks_entries_and_adds_unaccented_spellings(tmp_path):
    path = tmp_path / "la-wiktionary"
    write_bundle(
        path,
        [
            ("amō", '<a href="0000.xhtml#3">lātus</a> <a href="0000.xhtml#9">x</a>'),
            ("latus", "<h3>latus</h3>"),
            ("lātus", "<h3>lātus</h3>"),
        ],
        [("amāvistī", 0), ("lāta", 2)],
    )
    Bundle.read(path).relink({"0000.xhtml#3": "lātus"}).add_unaccented().write()

    stem = path / path.name
    words = [w for w, *_ in _records(stem.with_suffix(".idx"), ">II")]
    assert words == ["amō", "latus", "lātus"]
    synonyms = {(w, words[i]) for w, i in _records(stem.with_suffix(".syn"), ">I")}
    assert synonyms == {
        ("amāvistī", "amō"),
        ("amavisti", "amō"),
        ("amo", "amō"),
        ("lāta", "lātus"),
        ("lata", "lātus"),
        # latus is also the noun's word: lātus gets it as well, so both are found
        ("latus", "lātus"),
    }

    article = Bundle.read(path).articles[0]
    # A link to an entry not in the map is left alone
    assert article == '<a href="bword://lātus">lātus</a> <a href="0000.xhtml#9">x</a>'
    ifo = stem.with_suffix(".ifo").read_text(encoding="utf-8")
    assert "synwordcount=6\n" in ifo and ifo.startswith(
        "StarDict's dict ifo file\nversion=2.4.2\n"
    )


def test_bundle_takes_out_the_soft_hyphens_of_shared_labels(tmp_path):
    path = tmp_path / "la-wiktionary"
    write_bundle(
        path,
        [("et", "<p>and</p>"), ("e\u00adt", "<p>also</p>"), ("quī", "<p>who</p>")],
        [("quod", 2), ("q\u00aduod", 2), ("q\u00ad\u00aduod", 1)],
    )
    Bundle.read(path).unmark().write()

    stem = path / path.name
    words = [w for w, *_ in _records(stem.with_suffix(".idx"), ">II")]
    assert words == ["et", "et", "quī"]
    synonyms = [(w, i) for w, i in _records(stem.with_suffix(".syn"), ">I")]
    assert synonyms == [("quod", 1), ("quod", 2)]
