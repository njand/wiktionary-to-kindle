"""prepare-book: the Turkish suffix grammar, stem variants, candidate splits, the model
plumbing and the EPUB rewrite."""

import json
import zipfile

import pytest

from wiktionary_to_kindle.languages import tr_suffixes
from wiktionary_to_kindle.languages.tr_forms import stem_variants
from wiktionary_to_kindle.prepare import model
from wiktionary_to_kindle.prepare.epub import prepare_epub, prepare_xhtml
from wiktionary_to_kindle.prepare.lexicon import Lexicon, Sense
from wiktionary_to_kindle.prepare.segment import (
    HAIR,
    greedy,
    rooted,
    segment_text,
    target,
)
from wiktionary_to_kindle.utils import kindle_fold


@pytest.mark.parametrize(
    "stem, rest, analysis",
    [
        ("ev", "lerimizden", "plural + our + from (abl.)"),
        (
            "ev",
            "dekilerden",
            "in, at (loc.) + the one (that is) … (-ki) + plural + from (abl.)",
        ),
        ("gel", "miyor", "not + is …ing (progressive)"),
        ("ol", "ması", "…ing (verbal noun) + his/her/its"),
        ("gel", "eceğim", "will (future) + I"),  # K softens to ğ before a vowel
        ("kitap", "tan", "from (abl.)"),  # t after a voiceless consonant
        ("bekle", "niyor", "is …ed (passive) + is …ing (progressive)"),
        ("yaz", "ılmış", "is …ed (passive) + did, it seems (evidential past)"),
        ("bulut", "suz", "without (-sIz)"),
    ],
)
def test_suffix_chains(stem, rest, analysis):
    chains = tr_suffixes.chains_for(tr_suffixes.stem_class(stem))
    assert analysis in chains[rest]


def test_suffix_chains_follow_harmony():
    front = tr_suffixes.chains_for(tr_suffixes.stem_class("ev"))
    back = tr_suffixes.chains_for(tr_suffixes.stem_class("kız"))
    assert "lerimizden" in front and "lerimizden" not in back
    assert "larımızdan" in back


def test_suffix_entries_are_filed_with_a_hyphen():
    entry = next(iter(tr_suffixes.suffix_entries()))
    assert entry["word"].startswith("-") and entry["pos"] == "suffix"
    assert kindle_fold(entry["word"]) == kindle_fold(entry["word"][1:])


def test_stem_variants_from_the_entrys_own_forms():
    kitap = [
        {"form": "kitap", "tags": ["nominative", "singular"]},
        {"form": "kitabı", "tags": ["accusative", "definite", "singular"]},
    ]
    assert stem_variants(kitap, {"word": "kitap", "pos": "noun"}) == ["kitab"]
    oda = [
        {"form": "oda", "tags": ["nominative", "singular"]},
        {"form": "odayı", "tags": ["accusative", "definite", "singular"]},
    ]
    assert stem_variants(oda, {"word": "oda", "pos": "noun"}) == []
    git = [{"form": "gidiyor", "tags": []}, {"form": "gitti", "tags": []}]
    assert stem_variants(git, {"word": "gitmek", "pos": "verb"}) == ["gid"]
    bekle = [{"form": "bekliyor", "tags": []}]
    assert stem_variants(bekle, {"word": "beklemek", "pos": "verb"}) == ["bekli"]


def lexicon(words):
    """A Lexicon of {label: (headword, pos)}."""
    entries, by_fold = [], {}
    for label, (headword, pos) in words.items():
        by_fold.setdefault(kindle_fold(label), []).append(len(entries))
        entries.append(Sense(headword, pos, ""))
    return Lexicon(entries, by_fold)


LEXICON = lexicon(
    {
        "ev": ("ev", "noun"),
        "evler": ("ev", "noun"),
        "evi": ("ev", "noun"),
        "ol": ("olmak", "verb"),
        "olma": ("olmak", "verb"),
        "Ali": ("Ali", "name"),
        "alının": ("al", "noun"),
        "-de": ("-de", "suffix"),
    }
)


def test_target_only_for_words_that_miss_or_names():
    assert target(LEXICON, "evler") is None  # opens whole
    tgt = target(LEXICON, "evlerimizden")
    assert [s.stem for s in tgt.splits] == ["evler", "ev"]
    name = target(LEXICON, "Ali'nin")
    assert [s.stem for s in name.splits] == ["Ali'"]
    assert target(LEXICON, "Boris'in") is None  # no stem opens
    assert target(LEXICON, "dede") is None  # a suffix entry is no stem


def test_greedy_and_rooted():
    tgt = target(LEXICON, "olmasını")
    assert [s.stem for s in tgt.splits] == ["olma", "ol"]
    assert greedy([tgt], "") == [0]
    assert rooted([tgt], "") == [1]  # the stem of the lemma: ol + masını


def test_segment_text():
    text, report = segment_text("Evlerimizden çıktık. Ali'nin evi.", LEXICON, rooted)
    assert text == f"Ev{HAIR}lerimizden çıktık. Ali'{HAIR}nin evi."
    assert [word for word, _, split in report if split] == ["Evlerimizden", "Ali'nin"]


def test_model_answers_are_cached_and_validated(tmp_path):
    tgt = target(LEXICON, "olmasını")
    cache = model.Cache(tmp_path / "c.jsonl")

    class Fake(model.ModelDecider):
        def ask(self, targets, sentence):
            self.requests += 1
            return model.parse_answer(
                '{"words": [{"number": 1, "choice": 2, "lemma": "olmak"}]}'
            )

    decide = Fake(cache)
    assert decide([tgt], "S") == [1] and decide([tgt], "S") == [1]
    assert decide.requests == 1  # the second call came from the cache
    record = json.loads((tmp_path / "c.jsonl").read_text(encoding="utf-8"))
    assert record["split"] == f"ol{HAIR}masını" and record["lemma"] == "olmak"
    assert model.parse_answer("not json") == {}
    assert model.parse_answer(
        'x {"words": [{"number": 1, "choice": 9, "lemma": ""}]}'
    ) == {1: (9, "")}


def test_export_and_import(tmp_path):
    recorder = model.Recorder(None, rooted)
    segment_text("Olmasını bekledik.", LEXICON, recorder)
    requests = tmp_path / "requests.jsonl"
    model.export_requests(recorder, requests)
    request = json.loads(requests.read_text(encoding="utf-8"))
    assert "«Olmasını»" in request["prompt"] and "1: Olma + sını" in request["prompt"]
    answers = tmp_path / "answers.jsonl"
    answers.write_text(
        json.dumps(
            {
                "id": request["id"],
                "words": [{"number": 1, "choice": 1, "lemma": "olmak"}],
            }
        ),
        encoding="utf-8",
    )
    cache = model.Cache(tmp_path / "cache.jsonl")
    assert model.import_answers(requests, answers, cache, "test") == 1
    decide = model.CachedDecider(model.Cache(tmp_path / "cache.jsonl"))
    text, _ = segment_text("Olmasını bekledik.", LEXICON, decide)
    assert text == f"Olma{HAIR}sını bekledik."


def test_prepare_xhtml_keeps_markup():
    page = (
        '<html><head><title>Evlerimizden</title></head><body><p class="x">'
        "<i>Evlerimizden</i> &amp; evler.</p></body></html>"
    )
    out = prepare_xhtml(page, LEXICON, rooted, [], nowrap=True)
    assert "<title>Evlerimizden</title>" in out
    assert f'<i><span style="white-space: nowrap">Ev{HAIR}lerimizden</span></i>' in out
    assert "&amp; evler." in out


def test_prepare_epub(tmp_path):
    src, dst = tmp_path / "b.epub", tmp_path / "out.epub"
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr(
            "META-INF/container.xml",
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
            '<rootfile full-path="OEBPS/c.opf" media-type="application/oebps-package+xml"/>'
            "</rootfiles></container>",
        )
        z.writestr(
            "OEBPS/c.opf",
            '<package xmlns="http://www.idpf.org/2007/opf"><manifest>'
            '<item id="t" href="t.xhtml" media-type="application/xhtml+xml"/>'
            "</manifest></package>",
        )
        z.writestr("OEBPS/t.xhtml", "<html><body><p>Evlerimizden.</p></body></html>")
    report = prepare_epub(src, dst, LEXICON, rooted, nowrap=False)
    with zipfile.ZipFile(dst) as z:
        assert z.infolist()[0].filename == "mimetype"
        assert z.infolist()[0].compress_type == zipfile.ZIP_STORED
        assert f"Ev{HAIR}lerimizden." in z.read("OEBPS/t.xhtml").decode("utf-8")
    assert report[0][2].stem == "Ev"
