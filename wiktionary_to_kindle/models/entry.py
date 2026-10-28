import copy
import re

from ..utils import form_of_root, generate_vowel_variants, normalize, remove_breves
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
PATTERN_PERIPHRASTIC = r".* (sum|esse|fuisse|fore|erat|erit|est|sit|esset|iri|īrī)"
INVALID_PATTERN = re.compile(
    f"{PATTERN_INVALID_FORMS}|{PATTERN_CONTAINS_PLUS}|{PATTERN_PERIPHRASTIC}"
)


class Entry:
    def __init__(
        self,
        json_entry,
        id_number=1,
        alt_id=None,
        alt_page=None,
        examples_page=None,
        entry_ids=None,
        add_tags=True,
    ):
        self.json_entry = json_entry
        self.id_number = id_number
        self.alt_word = None
        self.alt_id = alt_id
        self.alt_page = alt_page
        self.examples_page = examples_page
        self.entry_ids = entry_ids

        self.head_word = None
        self.unmacronized_head_word = None
        self.headers = self.get_headers()
        if len(self.headers) > 0:
            self.head_word = remove_breves(self.headers[0].head_word)
            self.unmacronized_head_word = normalize(self.head_word)

        self.pos = json_entry.get("pos", None)
        self.senses_blocks = self.get_senses_blocks()
        self.etymology = self.get_etymology()
        self.descendants = self.get_descendants()
        self.no_senses = False
        self.inflected_forms = self.get_inflected_forms(add_tags)
        self.all_forms = self.get_all_forms()

        sorted_forms = sorted(self.all_forms, key=len, reverse=True)
        if sorted_forms:
            pattern = (
                r"\b(?:" + "|".join(map(re.escape, sorted_forms)) + r")(?:que|ne|ve)?\b"
            )
            self.bold_pattern = re.compile(pattern, flags=re.IGNORECASE)
        else:
            self.bold_pattern = None

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
                headers[-1].remainder += f"<br/>{header_text}"
                for header in headers:
                    header.num_headers = num_headers
        return headers

    def get_senses_blocks(self):
        blocks = []
        senses = self.json_entry.get("senses", [])
        # Hide "X of lemma" senses, unless that is all the entry has (its lemma is missing)
        pointer_senses = [
            "form_of" in sense and form_of_root(sense) for sense in senses
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

            examples = sense.get("examples", [])
            head_nr = sense.get("head_nr", 1)
            if head_nr > len(blocks):
                block = SensesBlock(
                    self,
                    len(blocks) + 1,
                    self.alt_word,
                    self.alt_id,
                    self.alt_page,
                    self.examples_page,
                )
                blocks.append(block)

            block.add_glosses(glosses, raw_glosses)
            sense_obj = block.lookup_sense(glosses, raw_glosses)
            sense_obj.add_examples(examples)

        if not blocks and senses:
            block = SensesBlock(
                self, 1, self.alt_word, self.alt_id, self.alt_page, self.examples_page
            )
            block.add_glosses(
                ["<i>Definition not available</i>"], ["<i>Definition not available</i>"]
            )
            blocks.append(block)

        return blocks

    def get_etymology(self):
        return Etymology(
            self.json_entry.get("etymology_text", None),
            self.json_entry.get("etymology_templates", []),
        )

    def get_descendants(self) -> list[tuple[str, str]]:
        """Extracts all descendant (lang_code, word) tuples, recursing into nested trees."""

        def _parse(nodes: list[dict]) -> list[tuple[str, str]]:
            results = []
            for node in nodes:
                word = node.get("word")
                lang_code = node.get("lang_code")

                if word:
                    results.append((lang_code, word))

                if "descendants" in node:
                    results.extend(_parse(node["descendants"]))
            return results

        raw_descendants = self.json_entry.get("descendants", [])
        return _parse(raw_descendants)

    def get_inflected_forms(self, add_tags=False):
        forms = {}
        for form_obj in self.json_entry.get("forms", []):
            form = form_obj.get("form")
            if (
                not form
                or form == self.head_word
                or "<" in form
                or ">" in form
                or INVALID_PATTERN.match(form)
            ):
                continue

            tags = set(form_obj.get("tags", []))
            filtered_tags = {
                "table-tags",
                "inflection-template",
                "error-unrecognized-form",
                "short-form",
                "conjugation-3",
                "uppercase",
                "class",
                "Medieval-Latin",
                "alternative",
                "stem",
            }
            if len(filtered_tags & tags) > 0:
                continue

            if form not in forms:
                forms[form] = Inflection(form, self)
            if add_tags:
                forms[form].add_tags(tags)
        return forms

    def get_all_forms(self):
        all_forms = set()
        for form in [header.head_word for header in self.headers] + list(
            self.inflected_forms.keys()
        ):
            all_forms.add(form)
            all_forms.update(generate_vowel_variants(form))
            all_forms.add(normalize(form))
        all_forms.discard("")
        return all_forms

    def id_path(self):
        return self.id_number

    def filter_descendants(self, filter_langs):
        if not filter_langs:
            return self.descendants
        # d[0] is lang_code, d[1] is word
        return [d for d in self.descendants if d[0] in filter_langs]

    def split(self, max_forms=200):
        split_entries = []
        if len(self.all_forms) <= max_forms:
            return [self]

        forms_chunk = set()
        for i, form in enumerate(sorted(self.all_forms)):
            forms_chunk.add(form)
            if len(forms_chunk) == max_forms or (i + 1 == len(self.all_forms)):
                split_entry = copy.deepcopy(self)
                split_entry.id_number = self.id_number + len(split_entries)
                split_entry.all_forms = forms_chunk

                # Recompile strict local regex pattern rather than duplicating a massive global one
                sorted_forms = sorted(forms_chunk, key=len, reverse=True)
                if sorted_forms:
                    pattern = (
                        r"\b(?:"
                        + "|".join(map(re.escape, sorted_forms))
                        + r")(?:que|ne|ve)?\b"
                    )
                    split_entry.bold_pattern = re.compile(pattern, flags=re.IGNORECASE)
                else:
                    split_entry.bold_pattern = None

                split_entry.inflected_forms = {}
                for f in forms_chunk:
                    if f in self.inflected_forms:
                        inflection = self.inflected_forms[f]
                        inflection.parent = split_entry
                        split_entry.inflected_forms[f] = inflection
                split_entries.append(split_entry)
                forms_chunk = set()
        return split_entries

    def __lt__(self, other):
        return self.unmacronized_head_word < other.unmacronized_head_word
