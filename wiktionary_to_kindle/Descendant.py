import re


class Descendant:
    def __init__(self, description, word):
        self.description = description
        self.word = word
        self.language = re.sub(r'[^\w\s]+', '', description).strip()
    
    def matches_lang(self, lang):
        return lang == self.language

    def matches_langs(self, langs):
        for lang in langs:
            if self.matches_lang(lang):
                return True
        return False
    
    def to_html(self):
        return f"<li><b>{self.description}:</b>{self.word}</li>"
