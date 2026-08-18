<source_code>
kindle_wiktionary/Descendant.py
```
import re


class Descendant:
    def __init__(self, description, word):
        self.description = description
        self.word = word
        self.language = re.sub(r'\W+', '', description)
    
    def matches_lang(self, lang):
        return lang == self.language

    def matches_langs(self, langs):
        for lang in langs:
            if self.matches_lang(lang):
                return True
        return False
    
    def to_html(self):
        return f"<li><b>{self.description}:</b>{self.word}</li>"
```

kindle_wiktionary/Entry.py
```
import re
import copy

from Header import Header
from Sense import SensesBlock
from Etymology import Etymology
from Descendant import Descendant
from Inflection import Inflection
from utils import remove_breves, normalize, generate_vowel_variants


INVALID_FORMS = {
     '-',
     '-us + future active indicative of sum',
     '-us + imperfect active indicative of sum',
     '-us + imperfect active subjunctive of sum',
     '-us + present active indicative of sum',
     '-us + present active subjunctive of sum',
     'Abarimōn gender unattested',
     'Abbreviation Cal.',
     'Alternative form of supplantātiō',
     'Feminine first declension noun.',
     'First-declension noun',
     'First-declension noun.',
     'Fourth-declension noun (all cases except the genitive singular in -ō)',
     'Future passive indicative',
     'Imperfect passive indicative',
     'Neuter first declension noun.',
     'Neuter third declension noun.',
     'Second-declension noun',
     'Synonym of iūgiter',
     'Third-declension noun',
     'Third-declension noun (Greek-type, normal variant).',
     'Third-declension noun (i-stem).',
     'Third-declension noun (neuter, imparisyllabic non-i-stem).',
     'Third-declension noun (neuter, parisyllabic non-i-stem).',
     'Third-declension noun or',
     'Third-declension noun.',
     'Third-declension participle. ¹When used purely as an adjective.',
     'Tubusuptu gender unattested',
     'aptus + future active indicative of sum',
     'aptus + imperfect active indicative of sum',
     'aptus + imperfect active subjunctive of sum',
     'aptus + present active indicative of sum',
     'aptus + present active subjunctive of sum',
     'capulātus + future active indicative of sum',
     'capulātus + imperfect active indicative of sum',
     'capulātus + imperfect active subjunctive of sum',
     'capulātus + present active indicative of sum',
     'capulātus + present active subjunctive of sum',
     'equidem quidem plus the demonstrative prefix e-',
     'factum + imperfect active subjunctive of sum',
     'factum + present active subjunctive of sum',
     'first',
     'first conjugation.',
     'first declension [first attested in 643]',
     'first declension}',
     'forms identical to feminine forms',
     'forms identical to masculine forms',
     'fourth-declension noun.',
     'highly defective',
     'i-stem',
     'in -er',
     'indeclinable portion with a first',
     'indeclinable portion with a first/second-declension adjective',
     'indeclinable portion with a numeral',
     'indeclinable portion with a relative',
     'indeclinable portion with a third-declension one-termination determiner',
     'indeclinable portion with a third-declension one-termination participle',
     'indeclinable portion with a third-declension two-termination numeral',
     'indefinite substantival pronoun',
     'interiectus + future active indicative of sum',
     'interiectus + imperfect active indicative of sum',
     'interiectus + imperfect active subjunctive of sum',
     'interiectus + present active indicative of sum',
     'interiectus + present active subjunctive of sum',
     'interrogative determiner',
     'interrogative determiner with an indeclinable portion',
     'interrogative pronoun',
     'interrogative pronoun with an Indeclinable portion',
     'interrogative pronoun with an indeclinable portion',
     'irregular alternative forms',
     'irregular conjugation',
     'irregular long ī',
     'irregular short imperative',
     'irregular short ă in most forms',
     'languidius comparative degree of languide',
     'minātus + future active indicative of sum',
     'minātus + imperfect active indicative of sum',
     'minātus + imperfect active subjunctive of sum',
     'minātus + present active indicative of sum',
     'minātus + present active subjunctive of sum',
     'no future',
     'no future active participle',
     'no gerund',
     'no imperative',
     'no passive',
     'no present stem',
     'no supine stem except in the future active participle',
     'non-neuter: Third-declension noun.',
     'optionally semi-deponent',
     'pedestris sometimes masculine',
     'plural only.',
     'relative',
     'ritratus gender unattested',
     'second-declension adjective',
     'second-declension adjective}',
     'second-declension numeral',
     'semi-deponent',
     'semi-indeclinable numeral',
     'singular only.',
     'superlative degree of prope',
     'supine stems',
     'supine stems except in the future active participle',
     'supine stemslactens',
     'third declension.',
     'third person -only in the passive',
     'third person-only',
     'third person-only in the passive',
     'variously declined',
     'with imperfect tense verbs',
     'zathenē gender unattested'
}


PATTERN_INVALID_FORMS = r'^(?:' + '|'.join(map(re.escape, INVALID_FORMS)) + r')$'
PATTERN_CONTAINS_PLUS = r'.*\+.*'
PATTERN_PERIPHRASTIC = r'.* (sum|esse|fuisse|fore|erat|erit|est|sit|esset|iri|īrī)$'
INVALID_PATTERN = re.compile(f"{PATTERN_INVALID_FORMS}|{PATTERN_CONTAINS_PLUS}|{PATTERN_PERIPHRASTIC}")


class Entry:
    def __init__(self, json_entry, id_number=1, alt_id=None, alt_page=None, examples_page=None, entry_ids=None,
                 add_tags=False):
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
                header = Header(plain_word, header_text, num_headers=len(self.json_entry["head_templates"]))
                headers.append(header)
            else:  # This type of template only contains a note, not the head word
                num_headers -= 1
                headers[-1].remainder += f"<br/>{header_text}"
                for header in headers:
                    header.num_headers = num_headers
            
        return headers

    def get_senses_blocks(self):
        blocks = []
        for i, sense in enumerate(self.json_entry["senses"]):
            if "form_of" in sense:  # Don't include senses that are just an inflection; they're handled by the base word.
                continue            
            
            glosses = sense.get("glosses", None)
            if glosses is None:
                continue
            raw_glosses = sense.get("raw_glosses", [])
            
            if "alt_of" in sense:
                self.alt_word = sense["alt_of"][0]["word"]
                if len(glosses) == 0 and len(raw_glosses) == 0 and "abbreviation" in sense.get("tags", []):
                    glosses = [self.alt_word]
                    raw_glosses = [f"Abbreviation of {self.alt_word}"]
            
            examples = sense.get("examples", [])

            head_nr = sense.get("head_nr", 1)
            if head_nr > len(blocks):
                block = SensesBlock(self, len(blocks) + 1, self.alt_word, self.alt_id, self.alt_page, self.examples_page)
                blocks.append(block)
            
            block.add_glosses(glosses, raw_glosses)
            sense = block.lookup_sense(glosses, raw_glosses)
            sense.add_examples(examples)

        return blocks

    def get_etymology(self):
        return Etymology(self.json_entry.get("etymology_text", None),
                         self.json_entry.get("etymology_templates", []))

    def get_descendants(self):
        descendants = []
        for descendant in self.json_entry.get("descendants", []):
            if len(descendant["templates"]) == 0:
                continue
            for line in descendant.get("text").split('\n'):
                try:
                    lang, word = line.split(':')
                    descendants.append(Descendant(lang, word))
                except ValueError:
                    continue
        return descendants
    
    def get_inflected_forms(self, add_tags=False):
        forms = {}
        for form_obj in self.json_entry.get("forms", []):
            form = form_obj.get("form")
            if form == self.head_word or INVALID_PATTERN.match(form):
                continue
            
            tags = set(form_obj.get("tags", []))
            filtered_tags = {'table-tags', 'inflection-template', 'error-unrecognized-form',
                             'short-form', 'conjugation-3', 'uppercase', 'class', 'Medieval-Latin',
                             'alternative', 'stem'}
            if len(filtered_tags & tags) > 0:
                continue
            
            if form not in forms:
                forms[form] = Inflection(form, self)
            
            if add_tags:
                forms[form].add_tags(tags)
        
        return forms
    
    def get_all_forms(self):
        all_forms = set()
        
        for form in [header.head_word for header in self.headers] + list(self.inflected_forms.keys()):
            all_forms.add(form)
            all_forms.update(generate_vowel_variants(form))
            all_forms.add(normalize(form))

        all_forms.discard('')
        
        return all_forms
        
    def id_path(self):
        return self.id_number
    
    def forms_html(self):
        html_lines = ['<idx:infl>']
        
        for form in sorted(self.all_forms):  
            if form == self.head_word:
                continue
            html_lines.append(f'<idx:iform value="{form}" exact="yes" />')
        
        if len(html_lines) == 1:
            return []
        
        html_lines.append('</idx:infl>')
        
        return html_lines
    
    def orth_html(self):
        html_lines = [f'<idx:orth value="{self.head_word}">{self.headers[0].to_html()}']
        
        html_lines.extend(self.forms_html())
        
        html_lines.append('</idx:orth>')
        
        return html_lines
    
    def pos_html(self):
        if self.pos is None:
            return []
        return [f'<p class="pos">{self.pos}</p>']
    
    def senses_html(self, link_examples=True, recursive=True):
        html_lines = []
        
        if len(self.senses_blocks) > len(self.headers):
            delete_idxs = []
            for i, senses_block in enumerate(self.senses_blocks):
                if len(senses_block.senses) == 0:
                    delete_idxs.append(i)
            for i in reversed(delete_idxs):
                self.senses_blocks.pop(i)
        
        if len(self.senses_blocks) == 0:
            self.no_senses = True
        
        for i, (senses_block, header) in enumerate(zip(self.senses_blocks, self.headers)):
            if i > 0:
                html_lines.append(header.to_html())
                html_lines.extend(self.pos_html())
            senses_lines, _ = senses_block.to_html(link_examples=link_examples, recursive=recursive)
            html_lines.extend(senses_lines)
        
        return html_lines
    
    def etymology_html(self):
        line = self.etymology.to_html()
        if line is None:
            return []
        
        return ["<h4>Etymology</h4>", line]

    def filter_descendants(self, filter_langs=None):
        if filter_langs is None:
            return self.descendants
        filtered = []
        for descendant in self.descendants:
            if descendant.matches_langs(filter_langs):
                filtered.append(descendant)
        return filtered
        
    def descendants_html(self, filter_langs=None):
        filtered_descendants = self.filter_descendants(filter_langs)
        if len(filtered_descendants) == 0:
            return []
        
        html_lines = ["<h4>Descendants</h4>", "<ul>"]
        for descendant in filtered_descendants:
            html_lines.append(descendant.to_html())
        html_lines.append("</ul>")

        return html_lines
    
    def to_html(self, filter_descendants_langs=None, link_examples=True, recursive_senses=True, include_etymology=True):
        html_lines = [f'<idx:entry name="Latin" scriptable="yes" spell="yes" exact="yes" id="{self.id_number}">']
        html_lines.extend(self.orth_html())
        html_lines.extend(self.pos_html())
        html_lines.extend(self.senses_html(link_examples, recursive_senses))
        if include_etymology:
            html_lines.extend(self.etymology_html())
        html_lines.extend(self.descendants_html(filter_descendants_langs))
        html_lines.append('</idx:entry>')
        
        if self.no_senses:
            return []
        return html_lines

    def inflections_html(self, inflection_max_senses=1):
        html_lines = []
        for i, (form, inflection) in enumerate(sorted(self.inflected_forms.items(), key=lambda item: item[1])):
            html_lines.extend(inflection.to_html(i+1, inflection_max_senses))
            html_lines.append("<hr/>")
        
        if len(html_lines) > 0:
            html_lines.pop()  # remove final horizontal rule
        
        return html_lines
    
    def examples_html(self, entry_page):
        html_lines = []
        
        for senses_block in self.senses_blocks:
            html_lines.extend(senses_block.examples_to_html())

        if len(html_lines) > 0:
            html_lines.insert(0, f'<a href="{entry_page}#{self.id_number}">↩</a>')
            html_lines.pop()  # remove final horizontal rule

        return html_lines
    
    def split(self, max_forms=200):
        """If there are too many inflections, split into multiple entries."""
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
                split_entry.inflected_forms = {}
                for form in forms_chunk:
                    if form not in self.inflected_forms:
                        continue
                    inflection = self.inflected_forms[form]
                    inflection.parent = split_entry
                    split_entry.inflected_forms[form] = inflection
                split_entries.append(split_entry)
                forms_chunk = set()
        
        return split_entries
        
    def __str__(self):
        return '\n'.join(self.to_html())
    
    def __lt__(self, other):
        return self.unmacronized_head_word < other.unmacronized_head_word
```

kindle_wiktionary/Etymology.py
```
import html


class Etymology:
    def __init__(self, etymology_text, etymology_templates):
        self.etymology_text = etymology_text
        self.etymology_templates = self.process_templates(etymology_templates)
    
    @staticmethod
    def wrap_elements(text, elements, wrapper="i"):
        if len(elements) == 0:
            return text
        
        wrapped = []
        cur_elem_idx = 0
        cur_elem = elements[cur_elem_idx]
        elem_matches = 0
        last_char_idx = 0
        for char_idx, char in enumerate(text):
            if char == cur_elem[elem_matches]:
                elem_matches += 1
                if elem_matches == len(cur_elem):                
                    wrapped.append(text[last_char_idx:char_idx - elem_matches + 1])
                    wrapped.append(f"<{wrapper}>")
                    wrapped.append(cur_elem)
                    wrapped.append(f"</{wrapper}>")
                    
                    cur_elem_idx += 1
                    if cur_elem_idx < len(elements):
                        cur_elem = elements[cur_elem_idx]
                    else:
                        wrapped.append(text[char_idx+1:])
                        last_char_idx = len(text) - 1
                        break
                    
                    last_char_idx = char_idx + 1
                    elem_matches = 0
            else:
                elem_matches = 0
        
        if last_char_idx + 1 < len(text):
            wrapped.append(text[last_char_idx:])
        
        return ''.join(wrapped)

    def process_templates(self, etymology_templates):
        processed_templates = []
        for template in etymology_templates:
            expansion = template.get("expansion", "")
            if len(expansion) > 0:
                processed_templates.append(expansion)
        return processed_templates
    
    def to_html(self):
        if self.etymology_text is None:
            return None
        
        formatted_etymology = self.wrap_elements(html.escape(self.etymology_text),
                                                self.etymology_templates, 'i')
        return f"<p>{formatted_etymology}</p>"
```

kindle_wiktionary/Example.py
```
import re


class Example:
    def __init__(self, example_json, parent_sense):
        self.parent_sense = parent_sense

        self.text = example_json.get("text", None)
        self.english = example_json.get("english", None)
        self.ref = example_json.get("ref", None)
        
        self.is_roman = False
        if "roman" in example_json:
            self.ref = self.text
            self.text = example_json["roman"]
            self.is_roman = True
    
    def get_parent_entry(self):
        parent_sense = self.parent_sense
        while True:
            parent_block = parent_sense.parent_block
            if isinstance(parent_block.parent, Entry):
                return parent_block.parent
            parent_sense = parent_block.parent
        
    def bold_word(self, text, parent_entry):
        """Find where the key word (possibly inflected) is used in the quote, and wrap it in bold tags"""
        # Sort subsequences by length (longest first) to prioritize longer matches
        all_forms = sorted(parent_entry.all_forms, key=len, reverse=True)
        pattern = r'\b(?:' + '|'.join(map(re.escape, all_forms)) + r')\b'

        # Wrap matches with <b></b> tags            
        bolded_text, n = re.subn(pattern, lambda m: f"<b>{m.group(0)}</b>", text, flags=re.IGNORECASE)
        
        return bolded_text
    
    def to_html(self):
        parent_entry = self.get_parent_entry()
        html_lines = ['<div class="quote">']
        example_line = self.bold_word(html.escape(self.text), parent_entry)
        if self.is_roman:
            html_lines.append(f'<p class="example roman">{example_line}</p>')
        else:
            html_lines.append(f'<p class="example">{example_line}</p>')
        if self.english is not None:
            html_lines.append(f'<p class="translation">{html.escape(self.english)}</p>')
        if self.ref is not None:
            html_lines.append(f'<p class="citation">{html.escape(self.ref)}</p>')
        html_lines.append('</div>')
        return html_lines
```

kindle_wiktionary/HTMLPage.py
```
import os


class HTMLPage:
    def __init__(self, max_lines=1000, output_fp_prefix="",
                 header_fp="../templates/html_header.txt",
                 footer_fp="../templates/html_footer.txt"):
        self.html_lines = []
        self.max_lines = max_lines
        self.entry_count = 0
        
        self.output_fp_prefix = output_fp_prefix
        self.index = 0
        self.output_fp = None
        self.update_output_fp()
        
        self.header = open(header_fp, "r", encoding="utf-8").read().split('\n')
        self.footer = open(footer_fp, "r", encoding="utf-8").read().split('\n')
        
        self.html_lines = list(self.header)
    
    def update_output_fp(self):
        self.output_fp = f"{self.output_fp_prefix}{self.index:04}.xhtml"
    
    def get_filename(self):
        """Return the filename without the base directory"""
        return os.path.basename(self.output_fp)
    
    def add_lines(self, lines: list):
        if len(lines) == 0:
            return
        
        self.html_lines.extend(lines)
        self.html_lines.append('<hr/>')

        self.entry_count += 1
        
        if len(self.html_lines) >= self.max_lines:
            self.write()
    
    def write(self):
        if self.entry_count == 0:
            return

        self.html_lines.extend(self.footer)
        with open(self.output_fp, "w", encoding="utf-8") as f:
            f.write('\n'.join(self.html_lines))
        
        self.html_lines = list(self.header)
        self.entry_count = 0
        self.index += 1
        self.update_output_fp()
```

kindle_wiktionary/Header.py
```
from utils import normalize, BREVE
import re


_ABBREVIATION_PATTERN = re.compile(
    r"\b(present infinitive|perfect active|supine|genitive|feminine|neuter)\b\s*"
)


class Header:
    def __init__(self, plain_word, full_header_text, num_headers=0):
        self.plain_word = plain_word
        self.full_header_text = full_header_text
        self.num_headers = num_headers
        
        self.head_word = None
        self.prefix = None
        self.remainder = None
        
        self.split_components()
    
    def split_components(self):
        unmacronized_text = normalize(self.full_header_text)
        
        start_idx = unmacronized_text.find(self.plain_word)
        end_idx = start_idx + len(self.plain_word)
        
        if start_idx == -1:  # word not found in expansion
            self.head_word = self.plain_word
            self.prefix = ''
            self.remainder = self.full_header_text
        else:
            last_end_idx = end_idx
            breve_count = 1
            while breve_count > 0:
                self.head_word = self.full_header_text[start_idx:end_idx]
                new_end_idx = end_idx + self.head_word.count(BREVE)
                breve_count = self.full_header_text[last_end_idx:new_end_idx].count(BREVE)
                if new_end_idx < len(self.full_header_text) and self.full_header_text[new_end_idx] == BREVE:
                    new_end_idx += 1
                last_end_idx = new_end_idx

            self.head_word = self.full_header_text[start_idx:last_end_idx]
            self.head_word = self.head_word.strip()
            
            self.prefix = self.full_header_text[:start_idx]
            self.remainder = self.full_header_text[last_end_idx:].strip()
            self.abbreviate_grammatical_forms()
    
    def abbreviate_grammatical_forms(self):
        cleaned = _ABBREVIATION_PATTERN.sub("", self.remainder)
        self.remainder = re.sub(r"\s{2,}", " ", cleaned).strip()
    
    def to_html(self):
        if self.num_headers == 1:
            return f"<h3>{self.prefix}{self.head_word}</h3>\n<i>{self.remainder}</i>"
        elif self.num_headers > 1:
            return f"<h3>{self.prefix}{self.head_word} <i>{self.remainder}</i></h3>"
```

kindle_wiktionary/Inflection.py
```
from MorphTag import MorphTag
from utils import normalize


class Inflection:
    def __init__(self, form, parent):
        self.form = form
        self.unmacronized_form = normalize(form)
        self.morph_tags = []
        self.parent = parent
    
    def add_tags(self, tags, verbose=False):
        new_tag = MorphTag(tags)
        if len(new_tag) == 0:
            return
        
        self.morph_tags.append(new_tag)
        self.combine_tags()
        self.clean_tags()
        
        if verbose:
            print(tags, '-->', [str(tag) for tag in self.morph_tags])
    
    def clean_tags(self):
        """Remove MorphTags that are purely a subset of another"""
        self.morph_tags.sort(key=len)
        
        remove_idxs = []
        for i, tag in enumerate(self.morph_tags[:-1]):
            for j, other_tag in enumerate(self.morph_tags[i+1:]):
                if tag.is_subset(other_tag):
                    remove_idxs.append(i)
                    break
        
        for idx in reversed(remove_idxs):
            self.morph_tags.pop(idx)

    def combine_tags(self):
        combined = []
        
        new_tag = self.morph_tags[-1]
        for i, tag in enumerate(self.morph_tags[:-1]):
            combined_tags = new_tag.combine(tag)
            if len(combined_tags) == 1:
                self.morph_tags = self.morph_tags[:i] + self.morph_tags[i+1:] + combined_tags
                return

    def orth_html(self):
        """Generate HTML lines for the <idx:orth> element and optional cross-reference."""
        root_word = self.parent.head_word
        root_id = self.parent.id_number
        root_page = self.parent.entry_ids.get(root_id, "ERROR-Root_not_found") if self.parent.entry_ids else ""

        html_lines = [
            f'<idx:orth value="{self.form}"><h3>{self.form}</h3></idx:orth>',
            f'<h4><i>(&lt; <a href="{root_page}#{root_id}">{root_word}</a>)</i></h4>'
        ]

        if self.unmacronized_form != self.form:
            html_lines.extend([
                '<idx:infl>',
                f'<idx:iform value="{self.unmacronized_form}" exact="yes" />',
                '</idx:infl>'
            ])

        return html_lines


    def definition_html(self, max_senses=1, link_examples=False, recursive=False):
        html_lines = []
        
        i = 0
        while max_senses > 0 and i < len(self.parent.senses_blocks):
            definitions, max_senses = self.parent.senses_blocks[i].to_html(max_senses, link_examples, recursive)
            html_lines.extend(definitions)
            i += 1
        
        return html_lines
    
    def parses_html(self):
        if len(self.morph_tags) == 0:
            return []
        
        self.morph_tags.sort()
        
        html_lines = ["<h4>Parses</h4>", "<ol>"]
        
        for tag in self.morph_tags:
            tag_str = str(tag)
            if len(tag_str) == 0:
                continue
            html_lines.append(f'<li class="tag">{tag_str}</li>')
        
        if len(html_lines) == 2:
            return []
        
        html_lines.append("</ol>")
        
        return html_lines
    
    def to_html(self, max_senses=1, link_examples=False, recursive=False):
        html_lines = [f'<idx:entry name="Latin" scriptable="yes" spell="yes" exact="yes" id="i{self.parent.id_number}">']
        html_lines.extend(self.orth_html())
        html_lines.extend(self.parent.pos_html())
        html_lines.extend(self.definition_html(max_senses, link_examples, recursive))
        html_lines.extend(self.parses_html())
        html_lines.append('</idx:entry>')

        return html_lines

    def __lt__(self, other):        
        return self.morph_tags[0] < other.morph_tags[0]
```

kindle_wiktionary/KindleDict.py
```
from Entry import Entry
from Header import Header
from HTMLPage import HTMLPage
from utils import normalize

import shutil
import re
import os
import json
import subprocess
from subprocess import CalledProcessError
from collections import defaultdict
from tqdm import tqdm


class KindleDict:
    def __init__(self, wiktionary_fp, lang_code, kindlegen_path):
        self.wiktionary_fp = wiktionary_fp
        self.lang_code = lang_code

        self.output_dir = self.ensure_unique_directory(f"../outputs/KindleDictionary-{self.lang_code}")
        self.output_sub_dir = self.output_dir + "/files"
        
        self.kindlegen_path = kindlegen_path

        self.entries = {}
        self.normalized_lemmas = defaultdict(set)
        self.entry_ids = {}
        self.current_json = None
        self.current_entry = None
        self.line_count = None
    
    @staticmethod
    def ensure_unique_directory(path):
        """Ensure the given directory exists. If it exists, create a unique version with a numerical suffix."""
        if not os.path.exists(path):
            return path

        base, counter = path, 1
        while os.path.exists(f"{base} ({counter})"):
            counter += 1

        new_path = f"{base} ({counter})"
        return new_path
    
    def init_dict_dir(self, css_fp="../templates/style.css",
                      cover_fp="../templates/cover.png"):
        os.makedirs(self.output_sub_dir)
        shutil.copy(css_fp, self.output_sub_dir)
        shutil.copy(cover_fp, self.output_sub_dir)

    @staticmethod
    def root_form(senses):
        if len(senses) == 0:
            return 0

        sense = senses[0]

        if "alt_of" in sense:
            return sense["alt_of"][0].get("word")
        elif "form_of" in sense:
            return sense["form_of"][0].get("word")

        links = sense.get("links", [])
        if len(links) != 1:
            return None
        link = links[0]
        if len(link) != 2 or not link[1].endswith("#Latin"):
            return None
        root_word = link[0]

        for gloss in sense.get("glosses", []):
            if gloss.endswith(f" of {root_word}"):
                return root_word

        return None
    
    @staticmethod
    def get_header(json_entry):
        plain_word = json_entry.get("word", "")
        
        if "head_templates" not in json_entry:
            header = Header(plain_word, "", num_headers=1)
        head_template = json_entry.get("head_templates", [{}])
        expansion = head_template[0].get('expansion', "")
        header = Header(plain_word, expansion, num_headers=1)

        return header.head_word

    @staticmethod
    def preprocess_addl_forms(json_entry):
        sense = json_entry.get("senses", [{}])[0]
        tags = sense.get("tags", [])
        
        processed_forms = []
        for form in json_entry.get("forms", []):
            if form.get("tags") == ["canonical"]:
                form["tags"] = tags
            processed_forms.append(form)
        
        return processed_forms
    
    def get_addl_forms(self, f, alt_positions, head_word, part_of_speech, seen_words=None, verbose=False):
#         if head_word == "commūniō":
#             verbose = True
       
        if seen_words is None:
            seen_words = set()
        
        seen_words.add(head_word)
        
        addl_forms = []
        
        if verbose:
            print("HEADWORD:", head_word)
            print("POS:", part_of_speech)
        
        for pos in alt_positions[(head_word, part_of_speech)]:
            f.seek(pos)
            line = f.readline()
            json_entry = json.loads(line)
            
            if verbose:
                print(self.preprocess_addl_forms(json_entry))
            
            addl_forms.extend(self.preprocess_addl_forms(json_entry))
            
            sub_head_word = self.get_header(json_entry)
            if sub_head_word in alt_positions and sub_head_word not in seen_words:
                if verbose:
                    print("RECURSE")
                addl_forms.extend(self.get_addl_forms(f, alt_positions, sub_head_word, seen_words, verbose))
        
        return addl_forms

    def make_sorted_path(self) -> str:
        """
        Given the input file path, return a path for the sorted version.
        Example: '../data/filtered_la.jsonl' -> '../data/filtered_la(sorted).jsonl'
        """
        base, ext = os.path.splitext(self.wiktionary_fp)
        return f"{base}(sorted){ext}"
    
    def sort_jsonl(self):
        """Sorts large JSONL file by normalized "word", to allow for more efficient processing."""
        EXCLUDED_POS = [
            'suffix',
            'character',
            'prefix',
            'symbol',
            'interfix',
            'infix',
            'circumfix',
            'punct'
        ]

        # First pass: Extract and normalize words, storing positions
        main_positions = defaultdict(list)
        alt_positions = defaultdict(list)  # store other word forms separately to add them to the main entries
        
        with open(self.wiktionary_fp, 'r', encoding='utf-8') as f:
            file_size = f.seek(0, 2)  # Move to end to get file size
            f.seek(0)  # Reset file pointer to the beginning

            with tqdm(total=file_size, unit="B", unit_scale=True, desc="Reading unsorted JSONL") as pbar:
                self.line_count = 0
                while True:
                    pos = f.tell()  # Get current file position
                    
                    line = f.readline()
                    if not line:
                        break  # Stop if end of file is reached
                    obj = json.loads(line)
                    word = normalize(obj["word"], lowercase=False)
                    header = self.get_header(obj)
                    part_of_speech = obj.get('pos')
                    
                    if (
                        part_of_speech in EXCLUDED_POS
                        or word.startswith('-')
                        or word.endswith('-')
                       ):
                        pass  # Skip this entry
                    else:
                        root = self.root_form(obj.get("senses", []))
                        
                        if root is None:
                            main_positions[(header, part_of_speech)].append(pos)
                            self.line_count += 1
                        else:
                            alt_positions[(root, part_of_speech)].append(pos)

                    pbar.update(f.tell() - pos)  # Update progress bar with bytes read
        
        output_path = self.make_sorted_path()
        
        # Second pass: Stream through file and write in sorted order
        with open(self.wiktionary_fp, 'r', encoding='utf-8') as f, open(output_path, 'w', encoding='utf-8') as out_f:
            with tqdm(total=self.line_count, unit="lines", unit_scale=True, desc="Writing sorted lines") as pbar:
                for (word, part_of_speech), positions in sorted(main_positions.items(),
                                              key=lambda item: (normalize(item[0][0], lowercase=True),
                                                                normalize(item[0][0], lowercase=False))):
                    addl_forms = self.get_addl_forms(f, alt_positions, word, part_of_speech)

                    for pos in positions:
                        f.seek(pos)  # Jump to the stored position
                        line = f.readline()
                        
                        if len(addl_forms) > 0:
                            json_entry = json.loads(line)
                            if "forms" not in json_entry:
                                json_entry["forms"] = []
                            json_entry["forms"].extend(addl_forms)
                            line = json.dumps(json_entry) + '\n'
                            
                        out_f.write(line)  # Write the line

                        pbar.update(1)
        
        self.wiktionary_fp = output_path
    
    def add_entry_to_dictionary(self, entry, html_pages, descendant_langs=None, link_examples=True,
                                recursive_senses=True, include_etymology=True):
        entry_filename = html_pages["main"].get_filename()
        self.entries.setdefault(entry.head_word, (entry.id_number, entry_filename))
        self.normalized_lemmas[normalize(entry.head_word, lowercase=True)].add(entry.id_number)
        self.entry_ids[entry.id_number] = entry_filename
        
        html_pages["main"].add_lines(entry.to_html(descendant_langs, link_examples, recursive_senses, include_etymology))
        
        if link_examples:
            entry_page = html_pages["main"].get_filename()
            html_pages["examples"].add_lines(entry.examples_html(entry_page))

    def count_lines(self):
        with open(self.wiktionary_fp, "rb") as f:
            self.line_count = sum(1 for _ in f)

    def make_opf(self, html_pages, header_fp="../templates/opf_header.txt", output_file="dictionary.opf"):
        entry_page_len = html_pages["main"].index
        inflection_page_len = html_pages["inflections"].index
        example_page_len = html_pages["examples"].index
        
        html_lines = open(header_fp, "r", encoding="utf-8").read().split('\n')
        
        for prefix, page_len in [("", entry_page_len), ("inf-", inflection_page_len), ("ex-", example_page_len)]:
            for page_num in range(page_len):
                html_lines.append(f'<item id="{prefix}page-{page_num}" href="{prefix}{page_num:04}.xhtml" media-type="application/xhtml+xml"/>')

        html_lines.append('</manifest>')
        html_lines.append('<spine>')
        
        for prefix, page_len in [("", entry_page_len), ("inf-", inflection_page_len), ("ex-", example_page_len)]:
            for page_num in range(page_len):
                html_lines.append(f'<itemref idref="{prefix}page-{page_num}"/>')

        html_lines.append('</spine>')
        html_lines.append('</package>')
        
        output_fp = os.path.join(self.output_dir, "files", output_file)
        with open(output_fp, "w", encoding="utf-8") as f:
            for lines in html_lines:
                f.write(lines)
                f.write('\n')
    
    def make_inflections_entries(self, html_pages, inflection_max_senses, limit):
        # TODO: Combine together multiple derivations into a single entry
        """
        Write inflections for exact matches to a form in a preceding entry,
        and also backfill the first occurrence, using byte offsets for efficiency.
        """
        previous_forms = {}   # form -> (byte_offset, id_number)
        created_forms = set() # forms we've already output HTML for

        def write_inflection(entry, form, norm_form, verbose=False):
            """Write inflection HTML for the given form in the given entry."""
            inflection = entry.inflected_forms.get(form)
            if inflection:
                html_pages["inflections"].add_lines(inflection.to_html(inflection_max_senses))
                created_forms.add(norm_form)
#                 if verbose:
#                     print(f"Writing form {form}.")

        def backfill_form(form, norm_form, file_obj, verbose=False):
            """Go back to the first occurrence and write its inflection if needed."""
            if norm_form not in previous_forms or norm_form in created_forms:
                if verbose:
                    print(f"Form '{form}' doesn't need to be backfilled.")
                return
            prev_offset, prev_id = previous_forms[norm_form]
            cur_pos = file_obj.tell()
            file_obj.seek(prev_offset)
            old_line = file_obj.readline()
            old_entry_json = json.loads(old_line)
            old_entry = Entry(old_entry_json, prev_id, None, None, None,
                              entry_ids=self.entry_ids, add_tags=True)
#             if verbose:
#                 print(f"Backfill head: {old_entry.head_word}")
                
            found_form = False
            for old_split in old_entry.split():
                for inf_form in old_split.inflected_forms:
                    if norm_form == normalize(inf_form, lowercase=True):
#                         if verbose:
#                             print(f"Found original form")
                            
                        write_inflection(old_split, inf_form, norm_form, verbose)
#                         if verbose:
#                             print(f"Wrote {form}")
                        
                        found_form = True
                        break
                if found_form:
                    break
#                 if verbose:
#                     print(f"{form} not in old_split")
            file_obj.seek(cur_pos)

        with open(self.wiktionary_fp, "r", encoding="utf-8") as f:
            last_entry_id = 0
            for _ in tqdm(range(limit), unit="lines", unit_scale=True, total=limit,
                          desc="Ambiguous inflections"):
                byte_offset = f.tell()
                line = f.readline()
                if not line:
                    break

                json_entry = json.loads(line)
                self.current_json = json_entry

                entry = Entry(json_entry, last_entry_id + 1, alt_id=None, alt_page=None,
                              examples_page=None, entry_ids=self.entry_ids, add_tags=True)
                self.current_entry = entry
                                
                entry_prev_forms = {}
                for split_entry in entry.split():
                    last_entry_id = split_entry.id_number

                    for form in split_entry.all_forms:
                        norm_form = normalize(form, lowercase=True)
                        verbose = False
#                         if norm_form in ["reducis", "magno", "ripam"]:
#                             verbose = True
#                         else:
#                             verbose = False
                        
                        lemma_ids = self.normalized_lemmas.get(norm_form, None)
#                         if verbose:
#                             print(f"\n{form} --> {norm_form}")
#                             print("lemma_ids:", lemma_ids)
                        if lemma_ids and last_entry_id in lemma_ids:
#                             if verbose:
#                                 print(f"Skipping backfilling for lemma_id: {last_entry_id}")
                            continue
                        
                        is_duplicate = norm_form in previous_forms or lemma_ids is not None

                        if is_duplicate:
#                             if verbose:
#                                 print(f"duplicate form: {norm_form} ({form}) < {split_entry.head_word}")
                            backfill_form(form, norm_form, f, verbose)
                            write_inflection(split_entry, form, norm_form, verbose)

                        if norm_form not in previous_forms:
#                             if verbose:
#                                 print(f"form: {norm_form} ({form}) not in previous forms")
                            entry_prev_forms[norm_form] = (byte_offset, entry.id_number)
                previous_forms.update(entry_prev_forms)
    
    def make_inflection_ids_unique(self):
        """
        Normalize <idx:entry ... id="..."> across all .xhtml files for inflected forms:
        - Guarantee uniqueness across all files
        - Stable order: files sorted by path, entries by appearance
        - Always add a numeric suffix (_0, _1, ...) for uniqueness
        """
        entry_pattern = re.compile(r'(<idx:entry[^>]*\bid=["\'])([^"\']+)(["\'])', re.IGNORECASE)

        # Step 1: Collect all inflected .xhtml files in stable order
        xhtml_files = []
        for root, _, files in os.walk(self.output_sub_dir):
            for fname in files:
                if fname.startswith("inf-") and fname.endswith(".xhtml"):
                    xhtml_files.append(os.path.join(root, fname))
        xhtml_files.sort()

        # Step 2: Read and collect entries in order
        file_contents = {}
        occurrences = []  # (path, start_pos, old_id, base)
        for path in xhtml_files:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            file_contents[path] = content

            for match in entry_pattern.finditer(content):
                old_id = match.group(2)
                occurrences.append((path, match.start(), old_id, old_id))

        # Step 3: Assign new ids per base, sequentially by appearance
        counters = defaultdict(int)
        new_ids = []  # parallel to occurrences
        for _, _, _, base in occurrences:
            new_id = f"{base}_{counters[base]}"
            new_ids.append(new_id)
            counters[base] += 1

        # Step 4: Rewrite files with replacements
        idx = 0
        for path in xhtml_files:
            content = file_contents[path]

            def repl(match):
                nonlocal idx
                new_id = new_ids[idx]
                idx += 1
                return f"{match.group(1)}{new_id}{match.group(3)}"

            new_content = entry_pattern.sub(repl, content)

            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
#                 print(f"Updated {path}")

    def make_mobi(self):
        opf_path = "dictionary.opf"
        mobi_name = f"{self.lang_code}-wiktionary.mobi"
        try:
            subprocess.run([
                self.kindlegen_path,
                opf_path,
                "-o", mobi_name
            ], cwd=self.output_sub_dir, check=True)
            
            shutil.move(os.path.join(self.output_sub_dir, mobi_name), os.path.join(self.output_dir, mobi_name))
        except CalledProcessError as e:
            print(e)
        
    def build_dictionary(self, max_page_len=5000, limit=None, descendant_langs=None, inflection_max_senses=1,
                         link_examples=True, recursive_senses=True, include_etymology=True, disambiguate_inflections=True):
        self.init_dict_dir()

        if limit is None:
            if self.line_count is None:
                self.count_lines()
            limit = self.line_count
        
        html_pages = {
            "main": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/'),
            "inflections": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/inf-'),
            "examples": HTMLPage(max_lines=max_page_len, output_fp_prefix=self.output_sub_dir + '/ex-')
        }
        
        last_entry_id = 0
        with open(self.wiktionary_fp, "r", encoding="utf-8") as f:
            for i, line in tqdm(enumerate(f), unit="lines", unit_scale=True, total=limit, desc="Building dictionary"):
                json_entry = json.loads(line)
                self.current_json = json_entry
                
                alt_id = alt_page = None
                if "alt_of" in json_entry:
                    alt_id, alt_page = self.entries.get(json_entry["alt_of"], (None, None))
                
                examples_page = html_pages["examples"].get_filename()

                entry = Entry(json_entry, last_entry_id+1, alt_id, alt_page, examples_page)
                self.current_entry = entry
                for split_entry in entry.split():
                    self.add_entry_to_dictionary(split_entry, html_pages, descendant_langs, link_examples,
                                                 recursive_senses, include_etymology)
                    last_entry_id = split_entry.id_number
                
                if len(self.entries) >= limit:
                    break
        
        if disambiguate_inflections:
            self.make_inflections_entries(html_pages, inflection_max_senses, limit=i+1)
        
        for title, page in html_pages.items():
            page.write()

        if disambiguate_inflections:
            self.make_inflection_ids_unique()

        self.make_opf(html_pages)
        
        print("Writing mobi...")
        self.make_mobi()
        print("Done!")
```

kindle_wiktionary/MorphTag.py
```
from collections import Counter


class MorphTag:
    GENDERS = ("masculine", "feminine", "neuter")
    CASES = ("nominative", "accusative", "genitive", "dative", "ablative", "vocative", "locative", "oblique")
    NUMBERS = ("singular", "plural")
    DEGREES = ("comparative", "superlative")
    PERSONS = ("first-person", "second-person", "third-person")
    TENSES = ("present", "imperfect", "future", "perfect", "pluperfect", "aorist", "preterite")
    MOODS = ("indicative", "subjunctive", "imperative", "conditional")
    VOICES = ("active", "passive")
    VERBAL_FORMS = ("infinitive", "participle", "supine", "gerund")
    MISC_FORMS = ("sigmatic", "adverb", "possessive", "diminutive", "romanization", "sometimes")
    
    NOUN_ADJ_ORDER = GENDERS + CASES + NUMBERS + DEGREES
    
    DEFAULT_ORDER = PERSONS + NUMBERS + TENSES + MOODS + VOICES + VERBAL_FORMS + MISC_FORMS

    ABBREVIATIONS = {
        "masculine": "m", "feminine": "f", "neuter": "n",
        "nominative": "nom", "accusative": "acc", "genitive": "gen", "dative": "dat",
        "ablative": "abl", "vocative": "voc", "locative": "loc", "oblique": "obl",
        "singular": "sg", "plural": "pl",
        "first-person": "1", "second-person": "2", "third-person": "3",
        "active": "act", "passive": "pass",
        "indicative": "ind", "subjunctive": "subj", "imperative": "imp", "conditional": "cond",
        "present": "pres", "imperfect": "impf", "future": "fut", "perfect": "perf", "pluperfect": "plup",
        "aorist": "aor", "preterite": "pret",
        "infinitive": "inf", "participle": "part", "supine": "sup", "gerund": "ger",
        "comparative": "comp", "superlative": "sup", "adverb": "adv", "possessive": "poss", "diminutive": "dim",
        "romanization": "rom", "sometimes": "smt", "sigmatic": "sig"
    }

    ABBREVIATED_ORDER = (
        "sg", "pl",
        "nom", "gen", "dat", "acc", "abl", "voc", "loc", "obl",
        "ind", "subj", "imp", "cond",
        "act", "pass",
        "pres", "impf", "fut", "perf", "plup", "aor", "pret",
        "1sg", "2sg", "3sg", "1pl", "2pl", "3pl",
        "inf", "part", "sup", "ger",
        "comp", "sup", "adv", "poss", "dim",
        "m", "f", "n",
        "rom", "smt", "sig"
    )
    
    CLASS_ABBREVIATIONS = {
        "GENDER": {"m", "f", "n"},
        "CASE": {"nom", "gen", "dat", "acc", "abl", "voc", "loc", "obl"},
        "NUMBER": {"sg", "pl"},
        "DEGREE": {"comp", "sup"},
        "MOOD": {"ind", "subj", "imp", "cond"},
        "VOICE": {"act", "pass"},
        "TENSE": {"pres", "impf", "fut", "perf", "plup", "aor", "pret"},
        "PERSON": {"1sg", "2sg", "3sg", "1pl", "2pl", "3pl"},
        "VERBAL_FORM": {"inf", "part", "sup", "ger"},
        "MISC_FORM": {"adv", "poss", "dim", "rom", "smt", "sig"}
    }
    ABBREVIATED_CLASS = {ab: c for c, abvs in CLASS_ABBREVIATIONS.items() for ab in abvs }

    def __init__(self, tags):
        self.tags = tags
        self.abbreviated_tags = self.abbreviate()
    
    def is_subset(self, other):
        return len(self.tags & other.tags) == len(self)
    
    def abbreviate(self):
        """
        Converts the Latin grammatical tags into abbreviated strings in sorted order.
        """
        sorted_tags = sorted(self.tags, key=lambda tag: (self.__class__.NOUN_ADJ_ORDER.index(tag)
                                                      if tag in self.__class__.NOUN_ADJ_ORDER else float('inf'),
                                                    self.__class__.DEFAULT_ORDER.index(tag)
                                                      if tag in self.__class__.DEFAULT_ORDER else float('inf')))
        
        filtered_tags = set()
        abbreviated_tags = []
        for tag in sorted_tags:
            if tag in self.__class__.ABBREVIATIONS:
                filtered_tags.add(tag)
                abbreviated_tags.append(self.__class__.ABBREVIATIONS[tag])
        self.tags = filtered_tags
        
        # Ensure person/number pairs are formatted correctly
        for person in ["1", "2", "3"]:
            for number in ["sg", "pl"]:
                if person in abbreviated_tags and number in abbreviated_tags:
                    abbreviated_tags.remove(person)
                    abbreviated_tags.remove(number)
                    abbreviated_tags.insert(0, person + number)
        
        return abbreviated_tags
    
    def combine(self, other):
        diffs = self.tags.symmetric_difference(other.tags)
        
        class_diffs = Counter()
        for tag in diffs:
            abbr = self.__class__.ABBREVIATIONS.get(tag)
            abbr_class = self.__class__.ABBREVIATED_CLASS.get(abbr)
            class_diffs[abbr_class] += 1
        
        if len(class_diffs) == 1:
            combined_tags = self.tags.union(other.tags)
            return [MorphTag(combined_tags)]
        
        return [self, other]
    
    def __str__(self):
        if len(self.abbreviated_tags) == 0:
            return ''
        
        tag_list = []
        for i, tag in enumerate(self.abbreviated_tags):
            tag_list.append(tag)
            if i + 1 < len(self.abbreviated_tags):
                next_tag = self.abbreviated_tags[i+1]
                if self.__class__.ABBREVIATED_CLASS.get(tag) == self.__class__.ABBREVIATED_CLASS.get(next_tag):
                    tag_list.append('/')
                else:
                    tag_list.append('.')
            else:
                tag_list.append('.')
            
        return ''.join(tag_list)

    def __len__(self):
        return len(self.tags)
    
    def __lt__(self, other):
        for abb in self.__class__.ABBREVIATED_ORDER:
            if abb in self.abbreviated_tags and abb not in other.abbreviated_tags:
                return True
            if abb in other.abbreviated_tags and abb not in self.abbreviated_tags:
                return False
```

kindle_wiktionary/Sense.py
```
import re

from Example import Example


class Sense:
    def __init__(self, parent_block, glosses, raw_glosses,
                 alt_word=None, alt_id=None, alt_page=None, examples_page=None,
                 bullet_id=1):
        self.parent_block = parent_block
        self.gloss = glosses[0]
        self.raw_gloss = raw_glosses[0]
        
        self.alt_word = alt_word
        self.alt_id = alt_id
        self.alt_page = alt_page
        
        self.examples_page = examples_page
        
        self.bullet_id = bullet_id
        self.examples = []
        
        self.sub_glosses = SensesBlock(self, 1, alt_word, alt_id, alt_page, examples_page)
        if len(glosses) > 1:
            self.sub_glosses.add_glosses(glosses[1:], raw_glosses[1:])
    
    def id_path(self):
        return f"{self.parent_block.id_path()}_{self.bullet_id}"
    
    def add_examples(self, examples):
        for example in examples:
            example_obj = Example(example, self)
            if example_obj.text is not None:
                self.examples.append(example_obj)
    
    @staticmethod
    def highlight_difference(a: str, b: str) -> str:
        """
        Wraps portions of `b` that are not in `a` with <i></i> tags.

        :param a: Subset string.
        :param b: Superset string.
        :return: Modified `b` with <i></i> tags around differences.
        """
        pattern = re.escape(a)
        if not a:
            return f"<i>{b}</i>"

        parts = re.split(f'({pattern})', b)

        return ''.join(f"<i>{part}</i>" if part != a else part for part in parts if part)
    
    def link_alt(self, gloss):
        if self.alt_word is None:
            return gloss
        
        pattern = re.escape(self.alt_word)
        return re.sub(pattern, lambda m: f'<a href="{self.alt_page}#{self.alt_id}">{m.group(0)}</a>', gloss)
    
    def to_html(self, link_examples=True, recursive=True):       
        formatted_gloss = self.highlight_difference(self.gloss, self.raw_gloss)
        formatted_gloss = self.link_alt(formatted_gloss)
        
        example_html = ""
        if link_examples and len(self.examples) > 0:
            link_text = "example"
            if len(self.examples) > 1:
                link_text = "examples"
            example_html = f' <sup><a class="noteref" href="{self.examples_page}#{self.id_path()}">{link_text}</a></sup>'
        
        html_lines = [f"<li>{formatted_gloss}{example_html}</li>"]
        
        if recursive:
            sub_gloss_lines, _ = self.sub_glosses.to_html()
            html_lines.extend(sub_gloss_lines)
        
        return html_lines
    
    def examples_to_html(self):
        html_lines = []
        if len(self.examples) > 0:
            html_lines.append(f'<aside class="footnote" id="{self.id_path()}">')
        
            for example in self.examples:
                html_lines.extend(example.to_html())

            html_lines.append("</aside>")
            html_lines.append("<hr/>")
        
        html_lines.extend(self.sub_glosses.examples_to_html())
        
        return html_lines


class SensesBlock:
    def __init__(self, parent, block_id, alt_word=None, alt_id=None, alt_page=None, examples_page=None):
        self.parent = parent
        self.block_id = block_id
        self.alt_word = alt_word
        self.alt_id = alt_id
        self.alt_page = alt_page
        self.examples_page = examples_page
        self.senses = {}
    
    def generate_all_variants(self, lst, spaces_left, start_idx=0, current_options=None):
        """
        Recursively generates all possible ways to insert empty strings into `lst`
        to match a target length by inserting exactly `spaces_left` empty strings.

        Args:
            lst (list): The list to generate variants for.
            spaces_left (int): The number of empty strings to insert.
            start_idx (int): The index from where the function should start inserting empty strings.
            current_options (list): The list that holds the current generated variants.

        Returns:
            list: A list containing all the possible variants of the list with empty strings inserted.
        """
        if current_options is None:
            current_options = []

        # If no more spaces are left to insert, add the current list as a variant
        if spaces_left == 0:
            current_options.append(lst)
            return current_options

        # Recursively insert empty strings at different positions
        for idx in range(start_idx, len(lst) + 1):
            self.generate_all_variants(lst[:idx] + [''] + lst[idx:], spaces_left - 1, idx + 1, current_options)

        return current_options

    @staticmethod
    def score_alignment(list1, list2):
        """
        Calculates the alignment score between two lists of strings.

        Args:
            list1 (list): The first list to compare.
            list2 (list): The second list to compare.

        Returns:
            int: The score representing the alignment quality.
        """
        score = 0
        for item1, item2 in zip(list1, list2):
            if len(item2) == 0:
                continue
            score += abs(len(item1) - len(item2))

        return score

    def align_lists(self, list1, list2):
        """
        Aligns two lists by inserting empty strings into the second list to minimize alignment score.

        Args:
            list1 (list): The first list.
            list2 (list): The second list.

        Returns:
            tuple: The aligned lists (list1, list2).
        """
        if len(list2) > len(list1):
            list2, list1 = self.align_lists(list2, list1)
            return list1, list2

        best_score = float('inf')
        best_variant = None
        for variant in self.generate_all_variants(list2, len(list1) - len(list2)):
            score = self.score_alignment(list1, variant)
            if score < best_score:
                best_score = score
                best_variant = variant

        return list1, best_variant

    def add_glosses(self, glosses, raw_glosses=None):
        if raw_glosses is None or len(raw_glosses) == 0:
            raw_glosses = glosses
        
        if len(glosses) != len(raw_glosses):
            glosses, raw_glosses = self.align_lists(glosses, raw_glosses)
            
        head_gloss = raw_glosses[0]
        if head_gloss not in self.senses:
            self.senses[head_gloss] = Sense(self, glosses, raw_glosses,
                                            self.alt_word, self.alt_id, self.alt_page, self.examples_page,
                                            bullet_id=len(self.senses) + 1)
        elif len(glosses) > 1:
            self.senses[head_gloss].sub_glosses.add_glosses(glosses[1:], raw_glosses[1:])
    
    def lookup_sense(self, glosses, raw_glosses=None):
        if raw_glosses is None or len(raw_glosses) == 0:
            raw_glosses = glosses
        
        if len(glosses) != len(raw_glosses):
            glosses, raw_glosses = self.align_lists(glosses, raw_glosses)
        
        sense_block = self
        sense = None
        while len(raw_glosses) > 0:
            head_gloss = raw_glosses.pop(0)
            if head_gloss not in sense_block.senses:
                return None
            sense = sense_block.senses[head_gloss]
            sense_block = sense.sub_glosses
        return sense
    
    def id_path(self):
        return f"{self.parent.id_path()}_{self.block_id}"
    
    def to_html(self, max_senses=None, link_examples=True, recursive=True):
        if len(self.senses) == 0:
            return [], max_senses
        
        html_lines = ["<ol>"]
        for i, (head_gloss, sense) in enumerate(self.senses.items()):
            if max_senses is None:
                html_lines.extend(sense.to_html(link_examples=link_examples, recursive=recursive))
            else:  # Abbreviated entry for inflected form
                html_lines.extend(sense.to_html(link_examples=False, recursive=False))
                max_senses -= 1
                if max_senses == 0:
                    if i + 1 < len(self.senses) or len(sense.sub_glosses.senses) > 0:
                        html_lines.append("<p>...</p>")
                    break
        
        html_lines.append("</ol>")
        return html_lines, max_senses
    
    def examples_to_html(self):
        html_lines = []
        for head_gloss, sense in self.senses.items():
            html_lines.extend(sense.examples_to_html())
        return html_lines
```

kindle_wiktionary/__init__.py
```
```

kindle_wiktionary/generate_mobi.py
```
import requests
import os
import gzip
import json
from tqdm import tqdm

from KindleDict import KindleDict


def download_file(url, dest_path):
    """Download the most recent dump of Wiktionary."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    with open(dest_path, 'wb') as f:
        for chunk in tqdm(response.iter_content(chunk_size=8192),
                          total=total_size//8192 + 1, unit='KB',
                          desc="Downloading Wiktionary dump"):
            f.write(chunk)

def filter_jsonl_gz_by_lang_code(src_gz_path: str, lang_code: str):
    dest_path = f"../data/filtered_{lang_code}.jsonl"
    total_uncompressed = 20 * 1024 ** 3

    with gzip.open(src_gz_path, 'rt', encoding='utf-8') as f_in, \
         open(dest_path, 'w', encoding='utf-8') as f_out, \
         tqdm(total=total_uncompressed, unit='B', unit_scale=True, desc="Filtering") as pbar:

        for line in f_in:
            pbar.update(len(line.encode('utf-8')))
            obj = json.loads(line)
            if obj.get('lang_code') == lang_code:
                f_out.write(line)
        
        pbar.total = pbar.n
        pbar.refresh()
    
    return dest_path

def download_wiktionary_languages(lang_codes: list[str]):
    """Download Wiktionary dump and filter to selected language(s)"""
    src_gz_path = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"
    gz_path = "../data/raw-wiktextract-data.jsonl.gz"

    download_file(src_gz_path, gz_path)
    file_paths = []
    for lang_code in lang_codes:
        fp = filter_jsonl_gz_by_lang_code(gz_path, lang_code)
        file_paths.append(fp)
    
    os.remove(gz_path)
    
    return file_paths

def find_kindlegen():
    possible_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Amazon\Kindle Previewer 3\lib\fc\bin\kindlegen.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Amazon\Kindle Previewer 3\lib\fc\bin\kindlegen.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Amazon\Kindle Previewer 3\lib\fc\bin\kindlegen.exe"),
    ]
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError("kindlegen.exe not found in common locations. Please verify its location and pass it in manually.")


if __name__ == "__main__":
    kindle_gen_path = find_kindlegen()

    lang_codes = ["la"]
    # file_paths = download_wiktionary_languages(lang_codes)
#     file_paths = ['../data/filtered_la(sorted)-short.jsonl']
    file_paths = ['../data/filtered_la(sorted).jsonl']
#     file_paths = ['../data/filtered_la.jsonl']

    for lang_code, input_fp in zip(lang_codes, file_paths):
        kd = KindleDict(input_fp, lang_code, kindle_gen_path)
#         kd.sort_jsonl()
        kd.build_dictionary(max_page_len=5000,
                            limit=None,
                            descendant_langs=["English", "Portuguese", "Spanish", "French", "Italian"],
                            link_examples=False,
                            recursive_senses=True,
                            include_etymology=True,
                            disambiguate_inflections=True)
```

kindle_wiktionary/utils.py
```
import unicodedata
from itertools import product


MACRON = '̄'
BREVE = '̆'
MACRONIZED_VOWELS = {
    "a": "ā", "A": "Ā",
    "e": "ē", "E": "Ē",
    "i": "ī", "I": "Ī",
    "o": "ō", "O": "Ō",
    "u": "ū", "U": "Ū",
    "y": "ȳ", "Y": "Ȳ"
}


def normalize(text: str, lowercase: bool = False) -> str:
    """Normalize text by stripping diacritics and optionally converting to lowercase."""
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    if lowercase:
        normalized = normalized.lower()
    return normalized


def remove_breves(text: str) -> str:
    """Remove breve diacritics from characters in a given string."""
    normalized = unicodedata.normalize("NFD", text)
    filtered = ''.join(c for c in normalized if c != BREVE)
    return unicodedata.normalize("NFC", filtered)


def generate_vowel_variants(word: str) -> list:
    """Generate all possible variants of a Latin word with only disputed vowel lengths changed."""
    decomposed = unicodedata.normalize("NFD", word)
    disputed_vowel_positions = []
    base_word_chars = []
    i = 0
    
    while i < len(decomposed):
        char = decomposed[i]
        base_word_chars.append(char)
        if i + 1 < len(decomposed) and decomposed[i+1] == MACRON:
            if i + 2 < len(decomposed) and decomposed[i+2] == BREVE:  # Check for disputed length marks
                disputed_vowel_positions.append(len(base_word_chars) - 1)
                i += 2
            else:
                base_word_chars[-1] = MACRONIZED_VOWELS.get(char, char)
                i += 1    
        i += 1
    
    base_word = unicodedata.normalize("NFC", "".join(base_word_chars))
    
    if not disputed_vowel_positions:
        return [base_word]
    
    variants = []
    for combination in product(*[(base_word[pos], MACRONIZED_VOWELS[base_word[pos]]) for pos in disputed_vowel_positions]):
        new_word = list(base_word)
        for pos, replacement in zip(disputed_vowel_positions, combination):
            new_word[pos] = replacement
        variants.append("".join(new_word))
    
    return variants
```

templates/html_footer.txt
```
</mbp:frameset>
</body>
</html>
```

templates/html_header.txt
```
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:mbp="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf" xmlns:idx="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<title>Latin-English Dictionary</title>
<link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<mbp:frameset>
```

templates/opf_header.txt
```
<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Latin-English Dictionary</dc:title>
<dc:language>en</dc:language>
<dc:identifier id="bookid">latin-dictionary</dc:identifier>
<meta name="cover" content="cover-image" />
<x-metadata>
<DictionaryInLanguage>la</DictionaryInLanguage>
<DictionaryOutLanguage>en</DictionaryOutLanguage>
<DefaultLookupIndex>Latin</DefaultLookupIndex>
</x-metadata>
</metadata>
<manifest>
<item id="cover-image" href="cover.png" media-type="image/png"/>
<item id="css" href="style.css" media-type="text/css"/>
```

templates/style.css
```
body {
    font-family: serif;
    margin: 1em;
}

b {
    font-size: 1.2em;
}

p {
    margin-left: 1em;
}

.pagebreak {
    page-break-before: always;
}

.tag {
    font-variant: small-caps;
}

.pos {
	font-style: italic;
}

.example {
	font-style: italic;
	color: #444;
	margin-left: 10px;
	padding: 5px 0;
}

.translation {
	color: #666;
	margin-top: 3px;
	padding-left: 10px;
}

.citation {
	font-size: 0.85em;
	font-style: italic;
	color: #555;
	margin-top: 8px;
	margin-left: 10px;
}

.roman {
	text-transform: uppercase;
}
```

</source_code>