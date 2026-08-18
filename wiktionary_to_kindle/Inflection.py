from .MorphTag import MorphTag
from .utils import normalize


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
