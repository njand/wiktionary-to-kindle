import html
import re

from jinja2 import Environment, PackageLoader


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


def format_example(example, parent_entry):
    """Helper passed to Jinja to execute regex bolding on key words."""
    text = html.escape(example.text)
    if parent_entry.bold_pattern is None:
        return text
    bolded_text, _ = parent_entry.bold_pattern.subn(
        lambda m: f"<b>{m.group(0)}</b>", text
    )
    return bolded_text


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
            "format_example": format_example,
        }
    )

    entry_tmpl = env.get_template("entry.html.jinja")
    inflection_tmpl = env.get_template("inflection.html.jinja")
    examples_tmpl = env.get_template("examples.html.jinja")

    @classmethod
    def render_entry(
        cls,
        entry,
        filter_descendants_langs=None,
        link_examples=True,
        recursive_senses=True,
        include_etymology=True,
    ):
        valid_pairs = [
            (block, header)
            for block, header in zip(entry.senses_blocks, entry.headers)
            if len(block.senses) > 0
        ]
        if not valid_pairs:
            entry.no_senses = True
            return []

        descendants = entry.filter_descendants(filter_descendants_langs)

        html_str = cls.entry_tmpl.render(
            entry=entry,
            valid_pairs=valid_pairs,
            descendants=descendants,
            link_examples=link_examples,
            recursive_senses=recursive_senses,
            include_etymology=include_etymology,
        )
        return html_str.strip().split("\n")

    @classmethod
    def render_inflections_html(cls, entry, max_senses=1, entry_ids=None):
        html_lines = []
        ids_map = entry_ids if entry_ids is not None else entry.entry_ids

        for i, (form, inflection) in enumerate(
            sorted(entry.inflected_forms.items(), key=lambda item: item[1])
        ):
            root_id = inflection.parent.id_number
            root_word = inflection.parent.head_word
            root_page = ids_map.get(root_id, "") if ids_map else ""

            html_str = cls.inflection_tmpl.render(
                inflection=inflection,
                index=i + 1,
                entry_id=entry.id,
                max_senses=max_senses,
                root_word=root_word,
                root_id=root_id,
                root_page=root_page,
            )
            html_lines.extend(html_str.strip().split("\n"))
            html_lines.append("<hr/>")

        if html_lines:
            html_lines.pop()
        return html_lines

    @classmethod
    def render_examples(cls, entry, entry_page):
        html_str = cls.examples_tmpl.render(entry=entry, entry_page=entry_page)
        lines = html_str.strip().split("\n")
        if len(lines) > 1 and lines[-1] == "<hr/>":
            lines.pop()

        return lines if len(lines) > 1 else []
