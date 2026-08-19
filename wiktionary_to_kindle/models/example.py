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
        from .entry import Entry  # Lazy import to avoid circular dependency

        while True:
            parent_block = parent_sense.parent_block
            if isinstance(parent_block.parent, Entry):
                return parent_block.parent
            parent_sense = parent_block.parent

    def bold_word(self, text, parent_entry):
        if parent_entry.bold_pattern is None:
            return text
        bolded_text, _ = parent_entry.bold_pattern.subn(
            lambda m: f"<b>{m.group(0)}</b>", text
        )
        return bolded_text
