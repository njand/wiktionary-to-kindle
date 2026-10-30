"""Rendering of entries to Kindle XHTML."""

import io

import pytest
from PIL import Image, ImageDraw

from wiktionary_to_kindle.languages import LATIN
from wiktionary_to_kindle.models.entry import Entry
from wiktionary_to_kindle.models.etymology import Etymology
from wiktionary_to_kindle.render.cover import (
    dictionary_cover,
    labelled_cover,
    title_lines,
)
from wiktionary_to_kindle.render.html_renderer import (
    HTMLRenderer,
    by_gloss,
    format_etymology,
    keep_spaces,
)
from wiktionary_to_kindle.render.shared_labels import mark, unmark
from wiktionary_to_kindle.utils import TEMPLATES

from .test_sort_merge import lemma


@pytest.mark.parametrize(
    "name",
    [
        "style.css",
        "cover-art.png",
        "DejaVuSerif.ttf",
        "DejaVuSerif-LICENSE.txt",
        "html_header.txt",
        "html_footer.txt",
        "opf_header.txt",
    ],
)
def test_templates_ship_inside_the_package(name):
    assert TEMPLATES.joinpath(name).is_file()


@pytest.mark.parametrize(
    "cover", [dictionary_cover("Ancient Greek"), labelled_cover("Device test", ["x"])]
)
def test_covers_are_small_kindle_pngs(cover):
    image = Image.open(io.BytesIO(cover))
    assert image.format == "PNG" and image.size == (800, 1280)
    assert len(cover) < 127 * 1024  # kindling warns about larger images


def test_each_language_gets_its_own_cover():
    assert dictionary_cover("Latin") != dictionary_cover("Turkish")


@pytest.mark.parametrize(
    "name, lines",
    [
        ("Latin", ["Latin-English"]),
        ("Turkish", ["Turkish-English"]),
        (
            "Ancient Greek",
            ["Ancient Greek-", "English"],
        ),  # never "Ancient" / "Greek-..."
    ],
)
def test_long_titles_break_after_the_language_name(name, lines):
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    assert [text for text, _ in title_lines(draw, name, 100)] == lines


def render(json_entry, descendant_langs=None):
    return "\n".join(
        HTMLRenderer.render_entry(Entry(json_entry, LATIN), descendant_langs)
    )


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
    assert html.count("<b>Fr.</b> aimer") == 1
    assert "<b>It.</b> amare" in html
    assert "amer" not in html


def cog(lang, term, expansion, **args):
    return {
        "name": "cog",
        "expansion": expansion,
        "args": {"1": lang, "2": term, **args},
    }


def inh(source, term, expansion, name="inh"):
    return {
        "name": name,
        "expansion": expansion,
        "args": {"1": "la", "2": source, "3": term},
    }


@pytest.mark.parametrize(
    "text, templates, expected",
    [
        # Only the cited word is italic, not the language or the gloss
        (
            "From Proto-Italic *rēks (“king”).",
            [inh("itc-pro", "*rēks", "Proto-Italic *rēks (“king”)")],
            "From Proto-Italic <i>*rēks</i> (“king”).",
        ),
        # Expansions are matched in order; a template without a cited word adds nothing
        (
            "Perhaps inherited from Old English beran and X.",
            [
                {"name": "glossary", "expansion": "i", "args": {"1": "inherited"}},
                cog("ang", "beran", "Old English beran"),
            ],
            "Perhaps inherited from Old English <i>beran</i> and X.",
        ),
        (
            "From A & B",
            [cog("en", "A & B", "A & B")],
            "From <i>A &amp; B</i>",
        ),
        (
            "From Proto-Indo-European *bʰer-.",
            [inh("ine-pro", "*bʰer-", "Proto-Indo-European *bʰer-")],
            "From PIE <i>*bʰer-</i>.",
        ),
        ("No templates", [], "No templates"),
        # Kaikki drops {{m}}: the word before a gloss is cited all the same (senium)
        (
            "From senex (“old man; aged”) or seneō (“to be weak, feeble”) + -ium.",
            [
                {
                    "name": "af",
                    "expansion": "seneō (“to be weak, feeble”) + -ium",
                    "args": {
                        "1": "la",
                        "2": "seneō",
                        "t1": "to be weak, feeble",
                        "3": "-ium",
                    },
                }
            ],
            (
                "From <i>senex</i> (“old man; aged”) or <i>seneō</i> (“to be weak, feeble”)"
                " + <i>-ium</i>."
            ),
        ),
        (
            "Present participle of oblīvīscor. From *(s)ker- (“to cut”), βάθος (báthos, “depth”).",
            [],
            (
                "Present participle of <i>oblīvīscor</i>. From <i>*(s)ker-</i> (“to cut”),"
                " <i>βάθος</i> (báthos, “depth”)."
            ),
        ),
        # {{ety}} repeats the tree before its prose, and gives each word with modifiers
        (
            (
                "Etymology tree\nLatin con-\nLatin pīlō\nLatin compīlō\n"
                "From con- (with) + pīlō + Gothic x."
            ),
            [
                {
                    "name": "ety",
                    "expansion": "Etymology tree\nLatin con-\nLatin pīlō\nLatin compīlō\n"
                    "From con- (with) + pīlō + Gothic x.",
                    "args": {
                        "1": "la",
                        "2": ":af",
                        "3": "con-<t:with>",
                        "4": "la:pīlō<id:to fix>",
                        "5": "ett:-",
                    },
                }
            ],
            "From <i>con-</i> (with) + <i>pīlō</i> + Gothic x.",
        ),
    ],
)
def test_format_etymology(text, templates, expected):
    assert format_etymology(Etymology(text, templates, "compilo")) == expected


def test_header_prefix_is_escaped_once():
    entry = lemma("amo", "verb", "<†> & amō (present infinitive amāre)", ["to love"])
    html = render(entry)
    assert "&lt;†&gt; &amp; amō" in html
    assert "&amp;lt;" not in html
    assert "&amp;amp;" not in html


def test_entries_say_their_style_in_markup():
    # kindling strips class attributes from entries, and the popup applies no stylesheet
    html = render(lemma("amo", "verb", "amō", ["to love"]))
    assert '<font size="+1"><b>amō</b></font></idx:orth> &#183; <i>verb</i></p>' in html
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
    assert "<i>(in sg.)</i> every" in html
    assert "<i>(in pl.)</i> all" in html


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
        '<p><b>Descendants.</b>&#160;<font size="-1" color="#555555"><b>Sp.</b> llave, '
        "clave &#183; <b>It.</b> chiave</font></p>"
    ) in html


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


def test_etymology_tree_is_cut_before_the_prose():
    text = (
        "Etymology tree\nLatin abyssus\nProto-Italic *-ālis\nLatin -ālis\n"
        "Latin abyssālis\nFrom abyssus + -ālis."
    )
    assert Etymology(text, [], "abyssalis").etymology_text == "From abyssus + -ālis."
    # A reconstructed word is starred
    starred = "Etymology tree\nLatin necō\nLatin *adnecō\nFrom ad- + necō."
    assert Etymology(starred, [], "adneco").etymology_text == "From ad- + necō."
    # No line for the word: left as it is, its lines run on
    other = "Etymology tree\nLatin ab\nFrom ab."
    assert (
        Etymology(other, [], "abc").etymology_text == "Etymology tree Latin ab From ab."
    )


def test_scripts_without_a_font_give_their_transliteration():
    text = (
        "Cognate with Gothic 𐌰𐍄𐌹𐍃𐌺 (atisk) and probably Gothic *𐌰𐌸𐌰𐌻𐌰𐍆𐌿𐌽𐍃 "
        "(*aþalafuns); compare Mycenaean Greek 𐁁𐀓𐀠𐀴𐀍 (a3-ku-pi-ti-jo, “Egyptian”) "
        "and Ancient Greek Αἴγυπτος (Aíguptos)."
    )
    gothic = cog("got", "𐌰𐍄𐌹𐍃𐌺", "Gothic 𐌰𐍄𐌹𐍃𐌺 (atisk)", tr="atisk")
    etymology = Etymology(text, [gothic])
    assert etymology.etymology_text == (
        "Cognate with Gothic atisk and probably Gothic *aþalafuns; compare Mycenaean "
        "Greek a3-ku-pi-ti-jo (“Egyptian”) and Ancient Greek Αἴγυπτος (Aíguptos)."
    )
    assert format_etymology(etymology).startswith("Cognate with Gothic <i>atisk</i>")


def test_headword_line_is_written_as_dictionaries_write_it():
    rex = lemma(
        "rex",
        "noun",
        "rēx m (genitive rēgis, feminine rēgīna); third declension",
        ["king"],
    )
    assert (
        '<font size="+1"><b>rēx</b></font></idx:orth>, rēgis <i>m.</i> '
        '&#183; <i>noun, 3rd decl.</i><br/><font size="-1"><i>fem.</i> rēgīna</font></p>'
    ) in render(rex)
    amo = lemma(
        "amo",
        "verb",
        "amō (present infinitive amāre, perfect active amāvī, supine amātum); "
        "first conjugation",
        ["to love"],
    )
    assert (
        "</idx:orth>, amāre, amāvī, amātum &#183; <i>verb, 1st conj.</i></p>"
        in render(amo)
    )
    part = lemma(
        "amatus",
        "participle",
        "amātus (feminine amāta, neuter amātum); first/second-declension participle",
        ["loved"],
    )
    assert ", amāta, amātum &#183; <i>participle, 1st/2nd decl.</i>" in render(part)
    # A line of another shape is only shortened
    odd = lemma("x", "noun", "x (a) (b); third declension", ["x"])
    assert "(a) (b); 3rd decl. &#183; <i>noun</i>" in render(odd)


def test_sense_labels_are_shortened():
    amo = lemma("amo", "verb", "amō", [])
    amo["senses"] = [
        {
            "glosses": ["to love"],
            "raw_glosses": ["(transitive, or in absolute use) to love"],
        }
    ]
    assert "<li><i>(trans., or absol.)</i> to love</li>" in render(amo)


def test_parts_of_speech_and_cases_are_spelled_as_dictionaries_do():
    cum = lemma("cum", "prep", "cum + ablative", ["with"])
    assert "</idx:orth> &#183; <i>preposition, + abl.</i></p>" in render(cum)
    cum = lemma("cum", "prep", "cum (+ ablative)", ["with"])
    assert "</idx:orth> &#183; <i>preposition, + abl.</i></p>" in render(cum)


def test_trailing_construction_and_shared_glosses_are_shortened():
    amo = lemma("amo", "verb", "amō", [])
    amo["senses"] = [
        {"glosses": ["to like"], "raw_glosses": ["to like [with infinitive]"]}
    ]
    assert "<li>to like <i>[w. inf.]</i></li>" in render(amo)
    assert by_gloss([("CAES", "a title"), ("C.", ""), ("CAESS", "a title")]) == [
        (["CAES", "CAESS"], "a title"),
        (["C."], ""),
    ]


def test_long_etymology_is_given_whole():
    # It closes the entry, so it is not shortened; each list item gets its own line
    items = ["Unknown; theories are:", "* From a Punic word.", "* From caesariēs."]
    text = "\n".join(items) + "\nDiscussion." * 40
    assert format_etymology(Etymology(text, [])) == (
        "Unknown; theories are:<br/>• From a Punic word.<br/>• From caesariēs."
        + " Discussion." * 40
    )
