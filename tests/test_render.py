"""Rendering of entries to Kindle XHTML."""

import pytest

from wiktionary_to_kindle.models.entry import Entry
from wiktionary_to_kindle.models.etymology import Etymology
from wiktionary_to_kindle.renderers.html_renderer import HTMLRenderer, format_etymology
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
    html = render(amo, ["French", "Italian"])
    assert "<b>French:</b> aimer" in html
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
