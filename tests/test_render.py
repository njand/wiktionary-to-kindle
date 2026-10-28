"""Rendering of entries to Kindle XHTML."""

from wiktionary_to_kindle.models.entry import Entry
from wiktionary_to_kindle.renderers.html_renderer import HTMLRenderer

from .test_sort_merge import lemma


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
