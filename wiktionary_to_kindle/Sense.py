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
        
        pattern = r'\b' + re.escape(self.alt_word) + r'\b'
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
