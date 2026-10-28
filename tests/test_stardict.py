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


def test_bundle_relinks_cards_and_adds_unaccented_spellings(tmp_path):
    path = tmp_path / "la-wiktionary"
    write_bundle(
        path,
        [
            ("amō", "<h3>amō</h3>"),
            ("latus", '<a href="0000.xhtml#2">lātus</a> <a href="0000.xhtml#3">x</a>'),
            ("lātus²", "<h3>lātus</h3>"),
        ],
        [("amāvistī", 0), ("lāta", 2), ("lātus", 2)],
    )
    Bundle.read(path).relink({"0000.xhtml#2": "lātus²"}).add_unaccented().write()

    stem = path / path.name
    words = [w for w, *_ in _records(stem.with_suffix(".idx"), ">II")]
    assert words == ["amō", "latus", "lātus²"]
    synonyms = {(w, words[i]) for w, i in _records(stem.with_suffix(".syn"), ">I")}
    assert synonyms == {
        ("amāvistī", "amō"),
        ("amavisti", "amō"),
        ("amo", "amō"),
        ("lāta", "lātus²"),
        ("lata", "lātus²"),
        ("lātus", "lātus²"),
        # latus is a word of its own (the card), so lātus does not add it again
        ("latus²", "lātus²"),
    }

    card = Bundle.read(path).articles[1]
    # A link to an entry not in the map is left alone
    assert card == '<a href="bword://lātus²">lātus</a> <a href="0000.xhtml#3">x</a>'
    ifo = stem.with_suffix(".ifo").read_text(encoding="utf-8")
    assert "synwordcount=7\n" in ifo and ifo.startswith(
        "StarDict's dict ifo file\nversion=2.4.2\n"
    )
