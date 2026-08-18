import re

class Descendant:
    def __init__(self, description, word):
        self.description = description
        self.word = word
        # Strip punctuation but retain internal spaces to allow specific language filtering
        self.language = re.sub(r'[^\w\s]+', '', description).strip()
    
    def matches_lang(self, lang):
        return lang == self.language

    def matches_langs(self, langs):
        return any(self.matches_lang(lang) for lang in langs)