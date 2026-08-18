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
        if parent_entry.bold_pattern is None:
            return text
            
        # Wrap matches with <b></b> tags using the pre-compiled regex
        bolded_text, n = parent_entry.bold_pattern.subn(lambda m: f"<b>{m.group(0)}</b>", text)
        
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
