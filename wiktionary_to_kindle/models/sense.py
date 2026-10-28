import difflib


class Sense:
    def __init__(
        self,
        glosses,
        raw_glosses,
        alt_word=None,
        alt_id=None,
        alt_page=None,
    ):
        self.gloss = glosses[0]
        self.raw_gloss = raw_glosses[0]
        self.alt_word = alt_word
        self.alt_id = alt_id
        self.alt_page = alt_page

        self.sub_glosses = SensesBlock(alt_word, alt_id, alt_page)
        if len(glosses) > 1:
            self.sub_glosses.add_glosses(glosses[1:], raw_glosses[1:])


class SensesBlock:
    def __init__(
        self,
        alt_word=None,
        alt_id=None,
        alt_page=None,
    ):
        self.alt_word = alt_word
        self.alt_id = alt_id
        self.alt_page = alt_page
        self.senses = {}

    def align_lists(self, list1, list2):
        """Aligns list2 to list1 using difflib to maximize semantic similarity."""
        matcher = difflib.SequenceMatcher(None, list1, list2)
        aligned_list2 = [""] * len(list1)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("equal", "replace"):
                for idx_1, idx_2 in zip(range(i1, i2), range(j1, j2)):
                    aligned_list2[idx_1] = list2[idx_2]
            elif tag == "insert":
                # Ignore extra elements in list2 to maintain core structure
                pass

        return list1, aligned_list2

    @staticmethod
    def align_to_raw(glosses, raw_glosses):
        """Kaikki leaves out a parent sense that is only a qualifier ("(as adjective)") from
        glosses but not from raw_glosses; give each such raw gloss an empty gloss. None if
        the glosses do not occur in the raw glosses in order."""
        aligned, rest = [], list(glosses)
        for raw in raw_glosses:
            if rest and rest[0] in raw:
                aligned.append(rest.pop(0))
            else:
                aligned.append("")
        return None if rest else aligned

    def add_glosses(self, glosses, raw_glosses=None):
        if raw_glosses is None or len(raw_glosses) == 0:
            raw_glosses = glosses
        if len(glosses) < len(raw_glosses):
            aligned = self.align_to_raw(glosses, raw_glosses)
            if aligned is not None:
                glosses = aligned
        if len(glosses) != len(raw_glosses):
            glosses, raw_glosses = self.align_lists(glosses, raw_glosses)

        head_gloss = raw_glosses[0]
        if head_gloss not in self.senses:
            self.senses[head_gloss] = Sense(
                glosses,
                raw_glosses,
                self.alt_word,
                self.alt_id,
                self.alt_page,
            )
        elif len(glosses) > 1:
            self.senses[head_gloss].sub_glosses.add_glosses(
                glosses[1:], raw_glosses[1:]
            )
