import html
import re

from jinja2 import Environment, PackageLoader

# kindling drops a space that stands alone between two inline elements ("</a> <i>" compiles
# to "</a><i>"), so the words run together; a no-break space survives
SPACE_BETWEEN_TAGS = re.compile(r"(</(?:a|b|i|span)>) +(?=<(?:a|b|i|span)\b)")


def keep_spaces(html_str):
    return SPACE_BETWEEN_TAGS.sub(r"\1&#160;", html_str)


def format_etymology(etymology):
    """Helper passed to Jinja to italicize each template expansion where it occurs in the text.

    Expansions are matched in order; one that does not occur after the previous match is skipped.
    """
    text = html.escape(etymology.etymology_text)
    wrapped, pos = [], 0
    for elem in etymology.etymology_templates:
        elem = html.escape(elem)
        start = text.find(elem, pos)
        if start == -1:
            continue
        wrapped.extend([text[pos:start], "<i>", elem, "</i>"])
        pos = start + len(elem)
    wrapped.append(text[pos:])
    return "".join(wrapped)


ORDINALS = {
    "first": "1st",
    "second": "2nd",
    "third": "3rd",
    "fourth": "4th",
    "fifth": "5th",
}
ORDINAL_PATTERN = re.compile(r"\b(" + "|".join(ORDINALS) + r")\b")
# Short names of the descendant languages, as Latin dictionaries write them
LANGUAGES = {
    "Italian": "It.",
    "Spanish": "Sp.",
    "Portuguese": "Pt.",
    "French": "Fr.",
    "English": "Eng.",
}


def compact_grammar(remainder, pos):
    """The headword line's grammar, shorter: "third declension" as "3rd decl.", and a
    closing part of speech the line names anyway left out
    ("first/second-declension participle" → "1st/2nd decl.")."""
    text = ORDINAL_PATTERN.sub(lambda m: ORDINALS[m.group(1)], remainder)
    text = re.sub(r"[- ]declension\b", " decl.", text)
    text = re.sub(r" conjugation\b", " conj.", text)
    if pos and text.endswith(" " + pos):
        text = text[: -len(pos) - 1]
    return text


def short_language(name):
    return LANGUAGES.get(name, name + ":")


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

    formatted = highlight_difference(sense.gloss, sense.raw_gloss)

    return link_alt(formatted, sense.alt_word, sense.alt_page, sense.alt_id)


class HTMLRenderer:
    env = Environment(loader=PackageLoader("wiktionary_to_kindle", "templates"))
    env.globals.update(
        {
            "format_gloss": format_gloss,
            "format_etymology": format_etymology,
            "compact_grammar": compact_grammar,
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
    def render_front(cls, dump_date, build_date, version):
        """Render the page before the entries: what the dictionary is, its sources and
        license (Wiktionary's CC BY-SA asks for attribution), and its version."""
        html_str = cls.front_tmpl.render(
            dump_date=dump_date, build_date=build_date, version=version
        )
        return html_str.strip().split("\n")
