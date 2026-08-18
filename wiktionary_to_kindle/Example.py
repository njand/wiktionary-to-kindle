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
        # Match base forms and optional enclitics (-que, -ne, -ve)
        pattern = r'\b(?:' + '|'.join(map(re.escape, all_forms)) + r')(?:que|ne|ve)?\b'

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
