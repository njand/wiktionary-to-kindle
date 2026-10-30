import html
import re

from jinja2 import Environment, PackageLoader

from .headline import headline_tail

# kindling drops a space that stands alone between two inline elements ("</a> <i>" compiles
# to "</a><i>"), so the words run together; a no-break space survives
SPACE_BETWEEN_TAGS = re.compile(r"(</(?:a|b|i|span|font)>) +(?=<(?:a|b|i|span|font)\b)")


def keep_spaces(html_str):
    return SPACE_BETWEEN_TAGS.sub(r"\1&#160;", html_str)


def format_etymology(etymology):
    """Helper passed to Jinja: the etymology as markup, with the words it cites in italics
    and Proto-Indo-European as PIE. It is given whole: it closes the entry, after the
    meanings. Its list items start lines of their own."""
    markup = _cite(etymology.etymology_text, etymology.templates)
    return markup.replace("Proto-Indo-European", "PIE").replace("\n", "<br/>")


def _cite(text, templates):
    """text escaped, with the words each template cites in italics where the template's
    expansion occurs. Expansions are matched in order; one that does not occur after the
    previous match is skipped."""
    text = html.escape(text)
    wrapped, pos = [], 0
    for template in templates:
        expansion = html.escape(template.expansion)
        start = text.find(expansion, pos)
        if start == -1:
            continue
        wrapped.extend([text[pos:start], _cite_template(template)])
        pos = start + len(expansion)
    wrapped.append(text[pos:])
    return "".join(wrapped)


def _cite_template(template):
    """The template's expansion escaped, with the words it cites in italics."""
    cited = html.escape(template.expansion)
    for term in template.terms:
        term = re.escape(html.escape(term))
        cited = re.sub(rf"(?<![\w<>/]){term}(?!\w)", r"<i>\g<0></i>", cited, count=1)
    return cited


# Short names of the descendant languages, as Latin dictionaries write them
LANGUAGES = {
    "Italian": "It.",
    "Spanish": "Sp.",
    "Portuguese": "Pt.",
    "French": "Fr.",
    "English": "Eng.",
    "Latin": "Lat.",
    "Greek": "Mod. Gk.",  # in a Greek entry, Modern Greek
}


def short_language(name):
    return LANGUAGES.get(name, name)


# The labels before a sense, as dictionaries shorten them: "(transitive) " → "trans."
SENSE_LABELS = {
    "transitive": "trans.",
    "intransitive": "intrans.",
    "ambitransitive": "trans. and intrans.",
    "in absolute use": "absol.",
    "reflexive": "refl.",
    "impersonal": "impers.",
    "figuratively": "fig.",
    "figurative": "fig.",
    "by extension": "by ext.",
    "literally": "lit.",
    "literal": "lit.",
    "transferred sense": "transf.",
    "metonymic": "meton.",
    "chiefly in the plural": "chiefly pl.",
    "usually in the plural": "usu. pl.",
    "in the plural": "in pl.",
    "in the singular": "in sg.",
    "plural only": "pl. only",
    "passive voice": "pass.",
    "with dative": "w. dat.",
    "with accusative": "w. acc.",
    "with ablative": "w. abl.",
    "with genitive": "w. gen.",
    "with infinitive": "w. inf.",
    "poetic": "poet.",
    "derogatory": "derog.",
    "historical": "hist.",
    "post-classical": "post-class.",
    "post-Classical": "post-class.",
    "pre-classical": "pre-class.",
    "Ecclesiastical Latin": "Eccl. Lat.",
    "Medieval Latin": "Med. Lat.",
    "New Latin": "New Lat.",
    "Late Latin": "Late Lat.",
    "Classical Latin": "Class. Lat.",
    "Old Latin": "Old Lat.",
    "Renaissance Latin": "Ren. Lat.",
    "Contemporary Latin": "Contemp. Lat.",
    "Greek mythology": "Gk. myth.",
    # Greek dialects
    "Epic": "Ep.",
    "chiefly Epic": "chiefly Ep.",
    "Homeric": "Hom.",
    "Attic": "Att.",
    "Ionic": "Ion.",
    "Doric": "Dor.",
    "Aeolic": "Aeol.",
    "Roman mythology": "Rom. myth.",
    "anatomy": "anat.",
    "astronomy": "astron.",
    "medicine": "med.",
    "botany": "bot.",
    "military": "mil.",
    "grammar": "gramm.",
    "mathematics": "math.",
    "philosophy": "philos.",
    "nautical": "naut.",
    "architecture": "archit.",
    "rhetoric": "rhet.",
    "chemistry": "chem.",
    "zoology": "zool.",
    "geometry": "geom.",
    "pathology": "pathol.",
    "religion": "relig.",
    "hapax legomenon": "hapax",
}
SENSE_LABEL_PATTERN = re.compile(
    r"(?<![\w-])("
    + "|".join(re.escape(k) for k in sorted(SENSE_LABELS, key=len, reverse=True))
    + r")(?![\w-])"
)
LEADING_LABELS = re.compile(r"^<i>\(([^()<>]*)\) </i>")
# A construction after the gloss: "<i> [with infinitive]</i>"
TRAILING_LABELS = re.compile(r"<i> \[([^\[\]<>]*)\]</i>$")


def short_sense_labels(gloss):
    """gloss with the labels around it shortened and out of their brackets:
    "<i>(transitive, or in absolute use) </i>to love" → "<i>trans., or absol.</i> to love",
    "to like<i> [with infinitive]</i>" → "to like <i>w. inf.</i>"."""

    def short(labels):
        return SENSE_LABEL_PATTERN.sub(lambda m: SENSE_LABELS[m.group(1)], labels)

    gloss = LEADING_LABELS.sub(lambda m: f"<i>{short(m.group(1))}</i> ", gloss)
    return TRAILING_LABELS.sub(lambda m: f" <i>{short(m.group(1))}</i>", gloss)


def by_gloss(words):
    """[(word, gloss)] as [([words], gloss)], words with the same gloss together, so a
    gloss is given once: "CAES, CAESS: either as a name or title"."""
    groups = {}
    for word, gloss in words:
        groups.setdefault(gloss or object(), ([], gloss))[0].append(word)
    return list(groups.values())


def format_gloss(sense):
    """Helper passed to Jinja to highlight differences and link alternate words."""

    def highlight_difference(a, b):
        # Escape Wiktionary HTML artifacts before generating safe XML components
        safe_a = html.escape(a) if a else ""
        safe_b = html.escape(b) if b else ""

        if not safe_a:
            return f"<i>{safe_b}</i>"
        pattern = re.escape(safe_a)
        parts = re.split(f"({pattern})", safe_b)
        return "".join(
            f"<i>{part}</i>" if part != safe_a else part for part in parts if part
        )

    def link_alt(gloss, alt_word, alt_page, alt_id):
        if alt_word is None or not alt_page or not alt_id:
            return gloss
        safe_alt = html.escape(alt_word)
        pattern = r"\b" + re.escape(safe_alt) + r"\b"
        return re.sub(
            pattern, lambda m: f'<a href="{alt_page}#{alt_id}">{m.group(0)}</a>', gloss
        )

    formatted = short_sense_labels(highlight_difference(sense.gloss, sense.raw_gloss))

    return link_alt(formatted, sense.alt_word, sense.alt_page, sense.alt_id)


class HTMLRenderer:
    env = Environment(loader=PackageLoader("wiktionary_to_kindle", "templates"))
    env.globals.update(
        {
            "format_gloss": format_gloss,
            "format_etymology": format_etymology,
            "by_gloss": by_gloss,
            "headline_tail": headline_tail,
            "short_language": short_language,
        }
    )

    entry_tmpl = env.get_template("entry.html.jinja")
    front_tmpl = env.get_template("front.html.jinja")

    @classmethod
    def render_entry(
        cls,
        entry,
        filter_descendants_langs=None,
        recursive_senses=True,
        include_etymology=True,
    ):
        """Render an entry indexed by its headword and all its forms."""
        valid_pairs = entry.valid_pairs()
        if not valid_pairs:
            return []

        descendants = entry.filter_descendants(filter_descendants_langs)

        html_str = cls.entry_tmpl.render(
            entry=entry,
            orth=entry.head_word,
            iforms=sorted(entry.all_forms - {entry.head_word}),
            valid_pairs=valid_pairs,
            descendants=descendants,
            recursive_senses=recursive_senses,
            include_etymology=include_etymology,
        )
        return keep_spaces(html_str).strip().split("\n")

    @classmethod
    def render_front(cls, language, dump_date, build_date, version):
        """Render the page before the entries: what the dictionary is, its sources and
        license (Wiktionary's CC BY-SA asks for attribution), and its version."""
        html_str = cls.front_tmpl.render(
            language=language,
            dump_date=dump_date,
            build_date=build_date,
            version=version,
        )
        return html_str.strip().split("\n")
