import re
import copy

from .Header import Header
from .Sense import SensesBlock
from .Etymology import Etymology
from .Descendant import Descendant
from .Inflection import Inflection
from .utils import remove_breves, normalize, generate_vowel_variants


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
        
        # Compile bolding regex once per entry to save CPU cycles
        sorted_forms = sorted(self.all_forms, key=len, reverse=True)
        if sorted_forms:
            pattern = r'\b(?:' + '|'.join(map(re.escape, sorted_forms)) + r')(?:que|ne|ve)?\b'
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

        # Create a list of valid pairs, ignoring empty sense blocks
        valid_pairs = [(block, header) for block, header in zip(self.senses_blocks, self.headers) if len(block.senses) > 0]
        
        if len(valid_pairs) == 0:
            self.no_senses = True
            
        for i, (senses_block, header) in enumerate(valid_pairs):
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
