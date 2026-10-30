import json

import pytest

from wiktionary_to_kindle.languages import LATIN
from wiktionary_to_kindle.quality import coverage, stats
from wiktionary_to_kindle.quality.corpus import clean, tokenize
from wiktionary_to_kindle.quality.labels import build_index, read_entries
from wiktionary_to_kindle.quality.notes import release_notes
from wiktionary_to_kindle.quality.sample import extract_sample
from wiktionary_to_kindle.utils import kindle_fold

from .test_sort_merge import ENTRIES


@pytest.mark.parametrize(
    "text, expected",
    [
        ("amō", "amo"),
        ("ROMA", "roma"),
        ("Cæsar", "caesar"),
        ("T-shirt", "tshirt"),
        ("ā̆b", "ăb"),  # a separate combining breve still counts
    ],
)
def test_kindle_fold(text, expected):
    assert kindle_fold(text) == expected


def entry(entry_id, orth, iforms=(), pos="noun"):
    infl = "".join(f'<idx:iform value="{f}" exact="yes" />' for f in iforms)
    return (
        f'<idx:entry name="Latin" id="{entry_id}"><h3><idx:orth value="{orth}">{orth}'
        f"<idx:infl>{infl}</idx:infl></idx:orth></h3>"
        f"<p><i>{pos}</i></p></idx:entry><hr/>"
    )


@pytest.fixture
def dict_dir(tmp_path):
    files = tmp_path / "files"
    files.mkdir()
    (files / "0000.xhtml").write_text(
        entry(1, "latus", ["lateris"])
        + entry(2, "lātus", ["latus", "lāta"], pos="adj")
        + entry(3, "amō", ["amo", "amāre", "amare"], pos="verb")
        + entry(4, "amārē", ["amare"], pos="adv"),
        encoding="utf-8",
    )
    (files / "card-0000.xhtml").write_text(
        entry("card_9", "lāta", ["lata"]), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def index(dict_dir):
    return build_index(read_entries(dict_dir / "files"))


@pytest.mark.parametrize(
    "word, outcome",
    [
        ("lateris", "unique"),
        ("AMO", "unique"),
        ("lātus", "spelling"),  # only the adjective is spelled exactly so
        ("latus", "ambiguous"),  # noun headword and the adjective's variant tie
        ("amāre", "spelling"),
        ("amare", "ambiguous"),
        ("lata", "spelling"),
        ("virum", "miss"),
    ],
)
def test_resolve(index, word, outcome):
    assert coverage.resolve(index, word)[0] == outcome


@pytest.mark.parametrize(
    "word, cause",
    [
        ("amoque", "enclitic -que"),
        ("XIV", "roman numeral"),
        ("Gallia", "unknown (capitalized)"),
        ("ferre", "unknown"),
    ],
)
def test_miss_cause(index, word, cause):
    assert coverage.miss_cause(index, word, LATIN) == cause


def test_miss_cause_spelling_variants(dict_dir):
    files = dict_dir / "files"
    (files / "0001.xhtml").write_text(
        entry(10, "vir", ["virum"]) + entry(11, "iam"), encoding="utf-8"
    )
    idx = build_index(read_entries(files))
    assert coverage.miss_cause(idx, "uir", LATIN) == "u for v"
    assert coverage.miss_cause(idx, "jam", LATIN) == "j for i"
    assert coverage.miss_cause(idx, "uirumque", LATIN) == "enclitic -que + u for v"


def test_measure_shares(index):
    report = coverage.measure(index, {"lateris": 3, "latus": 1, "virum": 4}, LATIN)
    assert report["tokens"] == 8
    assert report["token_share"]["miss"] == 0.5
    assert report["ambiguous_top"][0][:2] == ["latus", 1]


def test_stats_and_diff(dict_dir):
    current = stats.collect(dict_dir)
    assert current["entries"] == 4
    assert current["cards"] == 1
    assert current["pos"] == {"noun": 1, "adj": 1, "verb": 1, "adv": 1}

    previous = dict(current, entries=10, labels=current["labels"])
    markdown, regressions = stats.diff(previous, current)
    assert "| entries | 10 | 4 |" in markdown
    assert regressions == ["entries dropped -6 (-60.0%)"]


def test_clean_latin_library():
    raw = (
        "<html><head><title>Caesar</title></head><body><h1>DE BELLO</h1>"
        '<p class="internal_navigation"><a href="#1">1</a></p>'
        "<p>Gallia est omnis divisa &amp; ...</p>"
        '<div class="footer"><p><a>The Latin Library</a></p></div></body></html>'
    )
    words = tokenize(clean(raw, "latinlibrary"))
    assert "Gallia" in words and "Library" not in words and "Caesar" not in words
    assert "diuisa" in tokenize(clean(raw, "latinlibrary-u"))


def test_clean_macron_lines_and_tokenize():
    raw = "Notes in English.\nCum esset Caesar in citeriōre Gallia\nā̆b 12"
    text = clean(raw, "macron-lines")
    assert "English" not in text
    assert tokenize(text)["citeriōre"] == 1
    assert tokenize("ā̆b")["ā̆b"] == 1


TEI_EDITION = """<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><title>Ἰλιάς</title>
</teiHeader><text><body><div type="edition"><div type="textpart" n="1"><head>Α</head>
<l n="1"><milestone unit="para"/>μῆνιν ἄειδε θεὰ</l><l n="2">οὐλομένην, ἣ μυρίʼ<note>
Zenodotus</note> Ἀχαιοῖς</l></div><div type="textpart" n="2"><l>ἄλλοι μέν</l></div>
</div></body></text></TEI>"""


def test_clean_tei_keeps_the_edition_without_notes():
    assert clean(TEI_EDITION, "tei:1") == "μῆνιν ἄειδε θεὰ οὐλομένην, ἣ μυρίʼ Ἀχαιοῖς"
    words = tokenize(clean(TEI_EDITION, "tei"))
    assert "ἄλλοι" in words and "Ἰλιάς" not in words and "Zenodotus" not in words


CONLLU = """# sent_id = news_1
# text = Türkiye'nin başkenti Ankara'dır.
1-2	Türkiye'nin	_	_	_	_	_	_	_	_

# sent_id = ess_2
# text = Kimileri buna kader diyordu.
"""


def test_clean_conllu_by_genre_keeps_apostrophes():
    assert clean(CONLLU, "conllu:ess") == "Kimileri buna kader diyordu."
    words = tokenize(clean(CONLLU, "conllu"))
    assert words["Türkiye'nin"] == 1 and words["Ankara'dır"] == 1 and "nin" not in words
    assert tokenize("soldier’s, δʼ")["soldier’s"] == 1


def test_clean_wikisource_keeps_paragraphs_and_dialogue():
    raw = (
        '<table><tr><td><span class="ws-title">Yüksek Ökçeler</span></td></tr></table>'
        '<div>Çokdilli Vikikaynak</div><p id="a">Hatice Hanım dul kalmıştı.'
        '<sup class="reference"><a>[1]</a></sup></p><dl><dd>— Aman, aman!</dd></dl>'
        '<ol class="references"><li>somurtkan</li></ol>'
    )
    assert clean(raw, "wikisource") == "Hatice Hanım dul kalmıştı.\n— Aman, aman!"


def test_extract_sample_follows_pointer_chains(tmp_path):
    src = tmp_path / "dump.jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in ENTRIES),
        encoding="utf-8",
    )
    dst = tmp_path / "sample.jsonl"
    extract_sample(src, dst, LATIN, lemmas=0, include=["caussis"])
    with dst.open(encoding="utf-8") as f:
        words = {(e["word"], e["pos"]) for e in map(json.loads, f)}
    # caussis -> caussa -> causa: the lemma and every pointer to it come along
    assert words == {("caussis", "noun"), ("caussa", "noun"), ("causa", "noun")}


def coverage_report(**sources):
    """A coverage report with sources given as name=(tokens, opens, ambiguous)."""

    def summary(tokens, opens, ambiguous):
        share = {"unique": opens - ambiguous, "spelling": 0.0, "ambiguous": ambiguous}
        return {"tokens": tokens, "token_share": dict(share, miss=1 - opens)}

    report = {"sources": {k: summary(*v) for k, v in sources.items()}}
    report["overall"] = report["sources"]["all"]
    return report


def test_coverage_diff():
    old = coverage_report(
        caesar=(100, 0.9, 0.0), vergil=(50, 0.8, 0.0), all=(150, 0.87, 0.0)
    )
    same = coverage_report(
        caesar=(100, 0.898, 0.0), vergil=(50, 0.8, 0.004), all=(150, 0.87, 0.001)
    )
    markdown, regressions = coverage.diff(old, same)
    assert regressions == []
    assert "| caesar | 90.0% | 89.8% | -0.2 pp | 0.0% | 0.0% |" in markdown

    worse = coverage_report(
        caesar=(100, 0.85, 0.0), vergil=(60, 0.8, 0.02), all=(160, 0.84, 0.0)
    )
    _, regressions = coverage.diff(old, worse)
    # vergil's share left to index order rises, which only reorders the popup
    assert regressions == [
        "caesar: tokens that open something -5.0 pp",
        "all (150 → 160 tokens): tokens that open something -3.0 pp",
    ]


def test_coverage_diff_new_source_is_not_compared():
    old = coverage_report(caesar=(100, 0.9, 0.0), all=(100, 0.9, 0.0))
    new = coverage_report(
        caesar=(100, 0.9, 0.0), gate=(100, 0.5, 0.0), all=(200, 0.7, 0.0)
    )
    markdown, regressions = coverage.diff(old, new)
    assert regressions == []
    assert "| gate | | | new | | |" in markdown
    assert "| all | | | sources differ | | |" in markdown


def test_release_notes_lead_with_one_row_per_dictionary(tmp_path):
    def write(folder, entries, opens):
        folder.mkdir()
        figures = {"entries": entries, "mobi_bytes": 60_000_000}
        (folder / "stats-la.json").write_text(json.dumps(figures), encoding="utf-8")
        report = coverage_report(caesar=(100, opens, 0.0), all=(100, opens, 0.0))
        (folder / "coverage-la.json").write_text(json.dumps(report), encoding="utf-8")

    write(tmp_path / "old", 100, 0.9)
    write(tmp_path / "new", 120, 0.92)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "device-check-la.md").write_text("- [ ] `et`", encoding="utf-8")

    notes = release_notes(tmp_path / "new", tmp_path / "old", docs, intro="Built.")
    assert notes.startswith("Built.\n\n| Dictionary |")
    assert "| Latin | 120 | 92.0% | +2.0 pp | `la-wiktionary.mobi`, 60 MB |" in notes
    # The rest is folded away
    assert "<details><summary>Latin: index and coverage</summary>" in notes
    assert "<details><summary>Latin: device check</summary>\n\n- [ ] `et`" in notes

    first = release_notes(tmp_path / "new", None, docs)
    assert "| Latin | 120 | 92.0% | – |" in first
