"""Rendering of entries to Kindle XHTML."""

import pytest

from wiktionary_to_kindle.models.entry import Entry
from wiktionary_to_kindle.models.etymology import Etymology
from wiktionary_to_kindle.render.html_renderer import (
    HTMLRenderer,
    format_etymology,
    keep_spaces,
)
from wiktionary_to_kindle.render.shared_labels import mark, unmark
from wiktionary_to_kindle.utils import TEMPLATES

from .test_sort_merge import lemma


@pytest.mark.parametrize(
    "name",
    ["style.css", "cover.png", "html_header.txt", "html_footer.txt", "opf_header.txt"],
)
def test_templates_ship_inside_the_package(name):
    assert TEMPLATES.joinpath(name).is_file()


def render(json_entry, descendant_langs=None):
    return "\n".join(HTMLRenderer.render_entry(Entry(json_entry), descendant_langs))


def test_descendants_filtered_and_shown_by_language_name():
    amo = lemma("amo", "verb", "amō", ["to love"])
    amo["descendants"] = [
        {
            "lang": "Old French",
            "lang_code": "fro",
            "word": "amer",
            "descendants": [
                {"lang": "French", "lang_code": "fr", "word": "aimer"},
            ],
        },
        {"lang": "Italian", "lang_code": "it", "word": "amare"},
    ]
    amo["descendants"].append(
        {
            "lang": "Old French",
            "lang_code": "fro",
            "word": "amour",
            "descendants": [{"lang": "French", "lang_code": "fr", "word": "aimer"}],
        }
    )
    html = render(amo, ["French", "Italian"])
    assert html.count("<b>French:</b> aimer") == 1
    assert "<b>Italian:</b> amare" in html
    assert "amer" not in html


@pytest.mark.parametrize(
    "text, expansions, expected",
    [
        ("From X + aab tail", ["X", "ab"], "From <i>X</i> + a<i>ab</i> tail"),
        ("From X yz", ["Q", "X"], "From <i>X</i> yz"),
        ("From X and Y.", ["X", "Y"], "From <i>X</i> and <i>Y</i>."),
        ("From A & B", ["A & B"], "From <i>A &amp; B</i>"),
        ("No templates", [], "No templates"),
    ],
)
def test_format_etymology(text, expansions, expected):
    etymology = Etymology(text, [{"expansion": e} for e in expansions])
    assert format_etymology(etymology) == expected


def test_header_prefix_is_escaped_once():
    entry = lemma("amo", "verb", "<†> & amō (present infinitive amāre)", ["to love"])
    html = render(entry)
    assert "&lt;†&gt; &amp; amō" in html
    assert "&amp;lt;" not in html
    assert "&amp;amp;" not in html


def test_entries_say_their_style_in_markup():
    # kindling strips class attributes from entries, and the popup applies no stylesheet
    html = render(lemma("amo", "verb", "amō", ["to love"]))
    assert "<p><i>verb</i></p>" in html
    assert "class=" not in html


def test_qualifier_only_parent_senses_keep_their_children():
    # Kaikki leaves "(as adjective)" out of glosses but not raw_glosses (omnis)
    omnis = lemma("omnis", "adj", "omnis", [])
    omnis["senses"] = [
        {
            "glosses": ["every"],
            "raw_glosses": ["(as adjective)", "(in the singular) every"],
        },
        {"glosses": ["all"], "raw_glosses": ["(as adjective)", "(in the plural) all"]},
    ]
    html = render(omnis)
    assert "<li><i>(as adjective)</i><ol>" in html
    assert "<i>(in the singular) </i>every" in html
    assert "<i>(in the plural) </i>all" in html


def test_spaces_between_tags_survive_kindling():
    # kindling compiles "</i> <b>" to "</i><b>"
    entry = lemma("amo", "verb", "amō", ["to love"])
    html = render(entry)
    assert "</i> <b>" not in html
    assert keep_spaces("<a href='x'><b>amō</b></a> <i>verb</i> x") == (
        "<a href='x'><b>amō</b></a>&#160;<i>verb</i> x"
    )


def test_descendants_of_one_language_share_a_line():
    clavis = lemma("clavis", "noun", "clāvis", ["key"])
    clavis["descendants"] = [
        {"lang": "Spanish", "lang_code": "es", "word": "llave"},
        {"lang": "Italian", "lang_code": "it", "word": "chiave"},
        {"lang": "Spanish", "lang_code": "es", "word": "clave"},
        {"lang": "Spanish", "lang_code": "es", "word": "llave"},
    ]
    html = render(clavis)
    assert (
        "<li><b>Spanish:</b> llave, clave</li><li><b>Italian:</b> chiave</li>" in html
    )


@pytest.mark.parametrize(
    "label, count, expected",
    [
        ("et", 1, "e\u00adt"),
        ("ā", 2, "ā\u00ad\u00ad"),  # one letter: after it
        ("a\u0306b", 1, "a\u0306\u00adb"),  # a separate breve stays on its letter
    ],
)
def test_mark_puts_soft_hyphens_after_the_first_letter(label, count, expected):
    assert mark(label, count) == expected
    assert unmark(mark(label, count)) == label
