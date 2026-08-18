class Etymology:
    def __init__(self, etymology_text, etymology_templates):
        self.etymology_text = etymology_text
        self.etymology_templates = self.process_templates(etymology_templates)

    def process_templates(self, etymology_templates):
        processed_templates = []
        for template in etymology_templates:
            expansion = template.get("expansion", "")
            if len(expansion) > 0:
                processed_templates.append(expansion)
        return processed_templates