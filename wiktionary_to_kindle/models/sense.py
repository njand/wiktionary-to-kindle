import difflib
from .example import Example


class Sense:
    def __init__(
        self,
        parent_block,
        glosses,
        raw_glosses,
        alt_word=None,
        alt_id=None,
        alt_page=None,
        examples_page=None,
        bullet_id=1,
    ):
        self.parent_block = parent_block
        self.gloss = glosses[0]
        self.raw_gloss = raw_glosses[0]
        self.alt_word = alt_word
        self.alt_id = alt_id
        self.alt_page = alt_page
        self.examples_page = examples_page
        self.bullet_id = bullet_id
        self.examples = []

        self.sub_glosses = SensesBlock(
            self, 1, alt_word, alt_id, alt_page, examples_page
        )
        if len(glosses) > 1:
            self.sub_glosses.add_glosses(glosses[1:], raw_glosses[1:])

    def id_path(self):
        return f"{self.parent_block.id_path()}_{self.bullet_id}"

    def add_examples(self, examples):
        for example in examples:
            example_obj = Example(example, self)
            if example_obj.text is not None:
                self.examples.append(example_obj)


class SensesBlock:
    def __init__(
        self,
        parent,
        block_id,
        alt_word=None,
        alt_id=None,
        alt_page=None,
        examples_page=None,
    ):
        self.parent = parent
        self.block_id = block_id
        self.alt_word = alt_word
        self.alt_id = alt_id
        self.alt_page = alt_page
        self.examples_page = examples_page
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

    def add_glosses(self, glosses, raw_glosses=None):
        if raw_glosses is None or len(raw_glosses) == 0:
            raw_glosses = glosses
        if len(glosses) != len(raw_glosses):
            glosses, raw_glosses = self.align_lists(glosses, raw_glosses)

        head_gloss = raw_glosses[0]
        if head_gloss not in self.senses:
            self.senses[head_gloss] = Sense(
                self,
                glosses,
                raw_glosses,
                self.alt_word,
                self.alt_id,
                self.alt_page,
                self.examples_page,
                bullet_id=len(self.senses) + 1,
            )
        elif len(glosses) > 1:
            self.senses[head_gloss].sub_glosses.add_glosses(
                glosses[1:], raw_glosses[1:]
            )

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
