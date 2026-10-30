import re
import unicodedata

from ..merge.related import MERGED_KEY, related_lines
from ..utils import (
    capitalized,
    form_of_root,
    kindle_fold,
    remove_breves,
    sanitize_xhtml,
)
from .etymology import Etymology
from .header import Header
from .inflection import Inflection
from .sense import SensesBlock

INVALID_FORMS = {
    "-",
    "no future",
    "plural only.",
    "singular only.",
    "semi-deponent",
    "i-stem",
}
PATTERN_INVALID_FORMS = r"^(?:" + "|".join(map(re.escape, INVALID_FORMS)) + r")"
PATTERN_CONTAINS_PLUS = r".*\+.*"


def invalid_pattern(language):
    """Forms that are no words: table notes, sums, and forms made with an auxiliary."""
    patterns = [PATTERN_INVALID_FORMS, PATTERN_CONTAINS_PLUS]
    if language.periphrastic:
        patterns.append(language.periphrastic)
    return re.compile("|".join(patterns))


class Entry:
    def __init__(
        self,
        json_entry,
        language,
        id_number=1,
        alt_id=None,
        alt_page=None,
    ):
        self.json_entry = json_entry
        self.language = language
        self.id_number = id_number
        self.alt_word = None
        self.alt_id = alt_id
        self.alt_page = alt_page

        self.head_word = None
        self.headers = self.get_headers()
        if len(self.headers) > 0:
            self.head_word = remove_breves(self.headers[0].head_word)

        self.pos = json_entry.get("pos", None)
        head_templates = json_entry.get("head_templates") or [{}]
        self.pos = language.pos_by_head_template.get(
            head_templates[0].get("name"), self.pos
        )
        self.senses_blocks = self.get_senses_blocks()
        self.etymology = self.get_etymology()
        self.descendants = self.get_descendants()
        self.inflected_forms = self.get_inflected_forms()
        self.all_forms = self.get_all_forms()
        self.related = related_lines(
            json_entry.get(MERGED_KEY, []),
            " ".join(header.full_header_text for header in self.headers),
        )

    def get_headers(self):
        headers = []
        plain_word = self.json_entry.get("word", "")

        if "head_templates" not in self.json_entry:
            header = Header(plain_word, "", num_headers=1)
            headers.append(header)
            return headers

        num_headers = len(self.json_entry["head_templates"])
        for template in self.json_entry["head_templates"]:
            header_text = template["expansion"]
            if template["name"] != "tlb" or len(headers) == 0:
                header = Header(
                    plain_word,
                    header_text,
                    num_headers=len(self.json_entry["head_templates"]),
                )
                headers.append(header)
            else:
                num_headers -= 1
                headers[-1].remainder += f"<br/>{sanitize_xhtml(header_text)}"
                for header in headers:
                    header.num_headers = num_headers
        return headers

    def get_senses_blocks(self):
        blocks = []
        senses = self.json_entry.get("senses", [])
        # Hide "X of lemma" senses, unless that is all the entry has (its lemma is missing)
        pointer_senses = [
            "form_of" in sense and form_of_root(sense, self.language)
            for sense in senses
        ]
        if all(pointer_senses):
            pointer_senses = [False] * len(senses)
        for i, sense in enumerate(senses):
            if pointer_senses[i]:
                continue

            glosses = sense.get("glosses", None)
            raw_glosses = sense.get("raw_glosses", [])

            if not glosses:
                if raw_glosses:
                    glosses = raw_glosses
                else:
                    glosses = ["<i>Definition not available</i>"]
                    raw_glosses = ["<i>Definition not available</i>"]

            if "alt_of" in sense:
                self.alt_word = sense["alt_of"][0]["word"]
                if (
                    len(glosses) == 0
                    and len(raw_glosses) == 0
                    and "abbreviation" in sense.get("tags", [])
                ):
                    glosses = [self.alt_word]
                    raw_glosses = [f"Abbreviation of {self.alt_word}"]

            head_nr = sense.get("head_nr", 1)
            if head_nr > len(blocks):
                block = SensesBlock(self.alt_word, self.alt_id, self.alt_page)
                blocks.append(block)

            block.add_glosses(glosses, raw_glosses)

        if not blocks and senses:
            block = SensesBlock(self.alt_word, self.alt_id, self.alt_page)
            block.add_glosses(
                ["<i>Definition not available</i>"], ["<i>Definition not available</i>"]
            )
            blocks.append(block)

        return blocks

    def get_etymology(self):
        return Etymology(
            self.json_entry.get("etymology_text", None),
            self.json_entry.get("etymology_templates", []),
            self.json_entry.get("word", ""),
        )

    def get_descendants(self) -> list[tuple[str, str]]:
        """Extracts all descendant (language name, word) tuples, recursing into nested trees."""

        def _parse(nodes: list[dict]) -> list[tuple[str, str]]:
            results = []
            for node in nodes:
                word = node.get("word")
                lang = node.get("lang")

                if word:
                    results.append((lang, word))

                if "descendants" in node:
                    results.extend(_parse(node["descendants"]))
            return results

        raw_descendants = self.json_entry.get("descendants", [])
        return _parse(raw_descendants)

    def get_inflected_forms(self):
        invalid = invalid_pattern(self.language)
        forms = {}
        for form_obj in self.json_entry.get("forms", []):
            form = form_obj.get("form")
            if (
                not form
                or form == self.head_word
                or "<" in form
                or ">" in form
                or invalid.match(form)
            ):
                continue

            tags = set(form_obj.get("tags", []))
            # Alternative spellings are kept; merge_dump drops those with a page of their own
            filtered_tags = {
                "table-tags",
                "inflection-template",
                "error-unrecognized-form",
                "short-form",
                "uppercase",
                "class",
                "stem",
                "reconstruction",
            }
            if len(filtered_tags & tags) > 0:
                continue

            if form not in forms:
                forms[form] = Inflection(form, self)
            forms[form].add_tags(tags)
        return forms

    def get_all_forms(self):
        """Every spelling a tap should find this entry by, before label resolution.

        The device folds macrons and case itself, so no unmacronized or lowercase variants
        are added; see Language.lookup_spellings for the spellings that are.
        """
        all_forms = set()
        headwords = [header.head_word for header in self.headers]
        for form in headwords + list(self.inflected_forms.keys()):
            spellings = self.language.lookup_spellings(form)
            if self.language.capitalizes(self.pos, form in headwords):
                spellings += [capitalized(spelling) for spelling in spellings]
            all_forms.update(spellings)
        # A label of punctuation only (the Tironian et, ⁊) weighs nothing: no tap reaches it.
        # A symbol weighs nothing either, so "♃vis" (Iovis written with Jupiter's sign)
        # would be reached by "vis"; such forms are left out.
        return {
            form
            for form in all_forms
            if " " not in form
            and kindle_fold(form)
            and not any(unicodedata.category(char) == "So" for char in form)
        }

    def valid_pairs(self):
        """(senses block, header) pairs that render; an entry with none is left out."""
        return [
            (block, header)
            for block, header in zip(self.senses_blocks, self.headers)
            if len(block.senses) > 0
        ]

    def filter_descendants(self, filter_langs):
        """(language name, words) for each language in filter_langs (all if empty), in
        the order the tree first names them. A word reached through several branches
        (French "à l'onni" under three Old French words of omnis) is listed once."""
        by_lang = {}
        for lang, word in self.descendants:
            if not filter_langs or lang in filter_langs:
                by_lang.setdefault(lang, {})[word] = None
        return [(lang, list(words)) for lang, words in by_lang.items()]
