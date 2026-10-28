import json

import pytest

from wiktionary_to_kindle.quality import coverage, stats
from wiktionary_to_kindle.quality.corpus import clean, tokenize
from wiktionary_to_kindle.quality.labels import build_index, read_entries
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
        f'<p class="pos">{pos}</p></idx:entry><hr/>'
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
    (files / "inf-0000.xhtml").write_text(
        entry("inf_9_1", "lāta", ["lata"]), encoding="utf-8"
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
    assert coverage.miss_cause(index, word) == cause


def test_miss_cause_spelling_variants(dict_dir):
    files = dict_dir / "files"
    (files / "0001.xhtml").write_text(
        entry(10, "vir", ["virum"]) + entry(11, "iam"), encoding="utf-8"
    )
    idx = build_index(read_entries(files))
    assert coverage.miss_cause(idx, "uir") == "u for v"
    assert coverage.miss_cause(idx, "jam") == "j for i"
    assert coverage.miss_cause(idx, "uirumque") == "enclitic -que + u for v"


def test_measure_shares(index):
    report = coverage.measure(index, {"lateris": 3, "latus": 1, "virum": 4})
    assert report["tokens"] == 8
    assert report["token_share"]["miss"] == 0.5
    assert report["ambiguous_top"][0][:2] == ["latus", 1]


def test_stats_and_diff(dict_dir):
    current = stats.collect(dict_dir)
    assert current["entries"] == 4
    assert current["inflection_cards"] == 1
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


def test_clean_macron_lines_and_tokenize():
    raw = "Notes in English.\nCum esset Caesar in citeriōre Gallia\nā̆b 12"
    text = clean(raw, "macron-lines")
    assert "English" not in text
    assert tokenize(text)["citeriōre"] == 1
    assert tokenize("ā̆b")["ā̆b"] == 1


def test_extract_sample_follows_pointer_chains(tmp_path):
    src = tmp_path / "dump.jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in ENTRIES),
        encoding="utf-8",
    )
    dst = tmp_path / "sample.jsonl"
    extract_sample(src, dst, lemmas=0, include=["caussis"])
    with dst.open(encoding="utf-8") as f:
        words = {(e["word"], e["pos"]) for e in map(json.loads, f)}
    # caussis -> caussa -> causa: the lemma and every pointer to it come along
    assert words == {("caussis", "noun"), ("caussa", "noun"), ("causa", "noun")}
