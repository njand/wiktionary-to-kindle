"""Language profiles: what Latin, Ancient Greek and Turkish do their own way."""

import json

import pytest

from wiktionary_to_kindle.compiler import write_opf
from wiktionary_to_kindle.languages import (
    ANCIENT_GREEK,
    LANGUAGES,
    LATIN,
    TURKISH,
    grc,
    tr_forms,
)
from wiktionary_to_kindle.languages.grc import strip_length
from wiktionary_to_kindle.merge.sort import merge_dump
from wiktionary_to_kindle.models.entry import Entry
from wiktionary_to_kindle.quality.corpus import tokenize
from wiktionary_to_kindle.render.html_renderer import HTMLRenderer
from wiktionary_to_kindle.utils import MACRON, form_of_root, kindle_fold

from .test_sort_merge import lemma, pointer


def greek(entry):
    entry["lang_code"] = "grc"
    entry["head_templates"][0]["name"] = entry["head_templates"][0]["name"].replace(
        "la-", "grc-"
    )
    return entry


def test_languages_by_code():
    assert LANGUAGES == {"la": LATIN, "grc": ANCIENT_GREEK, "tr": TURKISH}
    assert LATIN.anchor == "#Latin"
    assert ANCIENT_GREEK.anchor == "#Ancient_Greek"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("λῡ̆́ω", "λύω"),  # macron and breve on one vowel
        ("ᾰ̓γᾰθός", "ἀγαθός"),  # breathing and accents stay
        ("λύω", "λύω"),
    ],
)
def test_strip_length_keeps_accents_and_breathings(text, expected):
    assert strip_length(text) == expected


def test_greek_letters_keep_their_accents_when_matching_pointers():
    assert ANCIENT_GREEK.letters("ὡς") != ANCIENT_GREEK.letters("ὥς")
    assert LATIN.letters("lātus") == LATIN.letters("latus")


def test_kindle_fold_weighs_text_as_written():
    # A decomposed macron and a Greek oxia are other characters to the device
    assert kindle_fold("ā") != kindle_fold("ā")
    assert kindle_fold("ά") != kindle_fold("ά")
    assert kindle_fold("Λόγος") != kindle_fold("λόγος")  # Greek case counts


def test_tokenize_keeps_the_text_as_printed():
    assert tokenize("λάω") == {"λάω": 1}


def test_form_of_link_names_the_language_section():
    sense = {
        "glosses": ["first-person singular future of λύω"],
        "links": [["λύω", "λύω#Ancient_Greek"]],
    }
    assert form_of_root(sense, ANCIENT_GREEK) == "λύω"
    assert form_of_root(sense, LATIN) is None


def test_greek_pointer_finds_its_lemma_by_letters_with_accents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = [
        greek(lemma("λύω", "verb", "λῡ̆́ω", ["to loose"])),
        # The target is the page title, without length marks
        greek(pointer("λύσω", "verb", "λῡ́σω", "future of λύω", "λύω")),
        greek(lemma("ὡς", "adv", "ὡς", ["as"])),
        # An unaccented target is no spelling of ὡς: it is left alone
        greek(pointer("ως", "adv", "ως", "misspelling of ως", "ως")),
    ]
    src = tmp_path / "kaikki-grc.jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    with open(merge_dump(str(src), ANCIENT_GREEK).path, encoding="utf-8") as f:
        merged = {e["word"]: e for e in map(json.loads, f)}
    assert "λύσω" not in merged  # merged into λύω, not an entry of its own
    # Greek pages are filed under their titles, which form-of links name
    assert "λύσω" in {f["form"] for f in merged["λύω"]["forms"]}
    assert "ως" not in {f["form"] for f in merged["ὡς"].get("forms", [])}


def test_greek_entry_is_indexed_under_its_language():
    entry = Entry(greek(lemma("λόγος", "noun", "λόγος", ["word"])), ANCIENT_GREEK)
    html = "\n".join(HTMLRenderer.render_entry(entry))
    assert '<idx:entry name="Greek"' in html


def test_front_page_and_package_name_the_language(tmp_path):
    front = "\n".join(
        HTMLRenderer.render_front(ANCIENT_GREEK, "2026-10-25", "2026-10-29", "0.1.0")
    )
    assert "<h1>Ancient Greek-English Dictionary</h1>" in front
    assert "<i>εἶ</i>" in front

    write_opf(str(tmp_path), ANCIENT_GREEK, 1, "2026-10-25", "2026-10-29", "0.1.0")
    opf = (tmp_path / "dictionary.opf").read_text(encoding="utf-8")
    assert "<DictionaryInLanguage>grc</DictionaryInLanguage>" in opf
    assert "<DefaultLookupIndex>Greek</DefaultLookupIndex>" in opf
    assert "ancient-greek-dictionary" in opf


@pytest.mark.parametrize(
    "word, causes, variant",
    [
        ("καλὸς", ("grave for acute",), "καλός"),
        ("Ἄνδρα", ("capitalized",), "ἄνδρα"),
        ("ἄνθρωπός", ("enclitic's accent",), "ἄνθρωπος"),
        ("ἐστίν", ("movable nu",), "ἐστί"),
        ("ἔλυσε", ("movable nu",), "ἔλυσεν"),
        ("δʼ", ("elision",), "δέ"),
        ("καθʼ", ("elision",), "κατά"),
        ("ἔφατʼ", ("elision",), "ἔφατο"),
        ("λ\u1f7bω", ("oxia or decomposed",), "λύω"),
        ("ἀγᾱθός", ("length marks",), "ἀγαθός"),  # marked where Wiktionary does not
        ("Καὶ", ("capitalized", "grave for acute"), "καί"),
    ],
)
def test_greek_miss_variants(word, causes, variant):
    assert (causes, variant) in ANCIENT_GREEK.miss_variants(word)


@pytest.mark.parametrize(
    "word, graved",
    [
        ("καλός", "καλὸς"),
        ("καί", "καὶ"),
        ("αὐτόν", "αὐτὸν"),
        ("λόγου", "λόγου"),  # the acute is not on the last syllable
        ("θεοῖς", "θεοῖς"),  # a circumflex stays
    ],
)
def test_with_grave(word, graved):
    assert grc.with_grave(word) == graved


def test_greek_lookup_spellings():
    # As most editions print it, and with its long vowels marked; no breves
    assert ANCIENT_GREEK.lookup_spellings("λῡ́ουσῐν") == [
        "λύουσιν",
        "λῡ́ουσιν",
        f"λύ{MACRON}ουσιν",  # the macron after the accented letter
    ]
    assert ANCIENT_GREEK.lookup_spellings("ᾰ̓γᾰθός") == ["ἀγαθός", "ἀγαθὸς"]
    assert ANCIENT_GREEK.lookup_spellings("χώρᾱν") == ["χώραν", "χώρᾱν"]


@pytest.mark.parametrize(
    "word, marked",
    [
        ("ἀπεκρῑ́θη", ["ἀπεκρῑ́θη", f"ἀπεκρί{MACRON}θη"]),
        ("ᾰ̓γᾰθός", ["ἀγαθός"]),  # short vowels are left plain
        ("λῡ̆́ω", ["λῡ́ω", f"λύ{MACRON}ω", "λύω"]),  # disputed length: both
        ("λόγος", ["λόγος"]),
    ],
)
def test_long_marked(word, marked):
    assert grc.long_marked(word) == marked


def test_greek_capitals_for_headwords_and_closed_classes():
    def labels(pos, word, forms):
        entry = greek(lemma(word, pos, word, ["x"], [(f, ["plural"]) for f in forms]))
        return Entry(entry, ANCIENT_GREEK).all_forms

    noun = labels("noun", "λόγος", ["λόγοι"])
    assert {"Λόγος", "λόγοι"} <= noun and "Λόγοι" not in noun
    assert {"Καί", "Καὶ"} <= labels("conj", "καί", [])
    assert "Ταῦτα" in labels("pron", "οὗτος", ["ταῦτα"])
    assert not any(
        w[0].isupper()
        for w in Entry(lemma("amo", "verb", "amō", ["love"]), LATIN).all_forms
    )


@pytest.mark.parametrize(
    "pos, word, expansion, shown",
    [
        (
            "noun",
            "λόγος",
            "λόγος • (lógos) m (genitive λόγου); second declension",
            "</idx:orth>, λόγου <i>ὁ</i> &#183; <i>noun, 2nd decl.</i>",
        ),
        (
            "adj",
            "ἀγαθός",
            "ᾰ̓γᾰθός • (ăgăthós) m (feminine ᾰ̓γᾰθή, neuter ᾰ̓γᾰθόν); first/second declension",
            "</idx:orth>, ᾰ̓γᾰθή, ᾰ̓γᾰθόν &#183; <i>adjective, 1st/2nd decl.</i>",
        ),
        ("verb", "λύω", "λῡ̆́ω • (lū̆́ō)", "</idx:orth> &#183; <i>verb</i>"),
    ],
)
def test_greek_head_line(pos, word, expansion, shown):
    entry = greek(lemma(word, pos, expansion, ["x"]))
    html = " ".join(HTMLRenderer.render_entry(Entry(entry, ANCIENT_GREEK)))
    assert f"<b>{entry_headword(expansion)}</b>" in html  # length marks shown
    assert shown in html
    assert f'<idx:orth value="{strip_length(entry_headword(expansion))}">' in html


def entry_headword(expansion):
    return expansion.split(" • ")[0]


def test_greek_auxiliary_forms_and_final_sigma():
    forms = [
        ("ἀγαπήσῃσ", ["second-person", "subjunctive"]),  # σ for ς in the table
        ("εἶεν", ["optative", "plural"]),
        ("third declension", ["participle"]),  # a table note filed as a form
    ]
    entry = greek(lemma("ἀγαπάω", "verb", "ἀγαπάω", ["to love"], forms))
    entry["forms"][1]["links"] = [["εἶεν", "ἠγαπημένοι#Ancient_Greek"]]
    labels = Entry(entry, ANCIENT_GREEK).all_forms
    assert "ἀγαπήσῃς" in labels and "ἀγαπήσῃσ" not in labels
    assert "εἶεν" not in labels  # εἰμί's, split off "ἠγαπημένοι εἶεν"
    assert "third declension" not in labels and "third" not in labels

    eimi = greek(lemma("εἰμί", "verb", "εἰμί", ["to be"], [("εἶεν", ["optative"])]))
    eimi["forms"][0]["links"] = [["εἶεν", "εἶεν#Ancient_Greek"]]
    assert "εἶεν" in Entry(eimi, ANCIENT_GREEK).all_forms


def test_kindle_fold_turkish_letters():
    # ı, İ, I and i weigh the same, as do the other Turkish letters and their base letters
    assert {kindle_fold(w) for w in ("kızı", "KIZI", "kizi", "Kİzİ")} == {"kizi"}
    assert kindle_fold("şoğüç") == "soguc"
    assert kindle_fold("Türkiye'nin") == "turkiyenin"


def test_turkish_skips_forms_with_spaces():
    assert TURKISH.skips_form({"form": "güzel miyim?"})
    assert TURKISH.skips_form({"form": "Çerkez?ik"})
    unrecognized = {"form": "güzeldim", "tags": ["error-unrecognized-form"]}
    assert not TURKISH.skips_form(unrecognized)  # an adjective's copula form
    assert LATIN.skips_form(unrecognized) and ANCIENT_GREEK.skips_form(unrecognized)
    assert TURKISH.lookup_spellings("evlerimiz") == ["evlerimiz"]
    assert not TURKISH.capitalizes("name", True)
    assert TURKISH.letters("kâğıt") == "kağıt"


def test_turkish_miss_variants():
    variants = list(TURKISH.miss_variants("Türkiye'nin"))
    assert variants[0] == (("apostrophe",), "Türkiye")
    assert (("stem + 1–2 letters",), "Türkiyen") in variants
    assert (("stem + 5+ letters",), "Türk") in variants
    stems = [variant for _, variant in TURKISH.miss_variants("evdeydi")]
    assert stems == [
        "evdeyd",
        "evdey",
        "evde",
        "evd",
    ]  # longest first, at least 3 letters


@pytest.mark.parametrize(
    "base, front, implied",
    [
        ("kadın", None, ["kadındı", "kadındır"]),
        ("kitap", None, ["kitaptı", "kitaptır"]),  # t after a voiceless consonant
        ("oğlu", None, ["oğluydu", "oğludur"]),  # y after a vowel
        ("göz", None, ["gözdü", "gözdür"]),
        ("saat", True, ["saatti", "saattir"]),  # a loanword's front suffixes
        ("TBMM", None, []),  # an abbreviation: its vowels are not written
    ],
)
def test_turkish_copula(base, front, implied):
    assert [spelling for spelling, _ in tr_forms.copula(base, front)] == implied


def test_turkish_copula_bases():
    forms = [
        {"form": "saat", "tags": ["nominative", "singular"]},
        {"form": "saate", "tags": ["dative", "singular"]},
        {"form": "saatim", "tags": ["first-person", "nominative", "possessive"]},
        {"form": "saati", "tags": ["third-person", "nominative", "possessive"]},
    ]
    implied = [s for s, _ in tr_forms.implied_forms(forms, set(), {"pos": "noun"})]
    # Only the bare nominative and the third person's: saatimdi paid too little
    assert implied == ["saatti", "saattir", "saatiydi", "saatidir"]
    var = {"word": "var", "pos": "adj", "senses": [{"glosses": ["existent"]}]}
    assert [s for s, _ in tr_forms.implied_forms([], set(), var)] == ["vardı", "vardır"]
    pointer = {
        "word": "iyice",
        "pos": "adv",
        "senses": [{"form_of": [{"word": "iyi"}]}],
    }
    assert tr_forms.implied_forms([], set(), pointer) == []
