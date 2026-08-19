from ..utils import normalize
from .morph_tag import MorphTag


class Inflection:
    def __init__(self, form, parent):
        self.form = form
        self.unmacronized_form = normalize(form, lowercase=True)
        self.morph_tags = []
        self.parent = parent

    def add_tags(self, tags, verbose=False):
        new_tag = MorphTag(tags)
        if len(new_tag) == 0:
            return
        self.morph_tags.append(new_tag)
        self.combine_tags()
        self.clean_tags()

    def clean_tags(self):
        self.morph_tags.sort(key=len)
        remove_idxs = []
        for i, tag in enumerate(self.morph_tags[:-1]):
            for j, other_tag in enumerate(self.morph_tags[i + 1 :]):
                if tag.is_subset(other_tag):
                    remove_idxs.append(i)
                    break
        for idx in reversed(remove_idxs):
            self.morph_tags.pop(idx)

    def combine_tags(self):
        new_tag = self.morph_tags[-1]
        for i, tag in enumerate(self.morph_tags[:-1]):
            combined_tags = new_tag.combine(tag)
            if len(combined_tags) == 1:
                self.morph_tags = (
                    self.morph_tags[:i] + self.morph_tags[i + 1 :] + combined_tags
                )
                return

    def __lt__(self, other: "Inflection") -> bool:
        # Fallback to an empty string key if morph_tags is empty []
        key_self = (self.morph_tags[0] if self.morph_tags else "", self.form)
        key_other = (other.morph_tags[0] if other.morph_tags else "", other.form)
        return key_self < key_other
