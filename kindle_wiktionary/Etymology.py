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
