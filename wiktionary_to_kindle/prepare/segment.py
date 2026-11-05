"""Where a Turkish word may be split, and which words need it.

A word is split, with a hair space (U+200A) between its stem and its suffix chain, only
when a tap on it whole would open nothing, or, for a name with suffixes after an
apostrophe (Ali'nin), would open other words than the name (alının). A split is a
candidate only if its stem opens a word of the dictionary and its rest is a chain the
suffix grammar spells after that kind of stem (languages.tr_suffixes), so every split a
reader sees can be looked up, half by half. Which candidate is right is decided elsewhere:
by the longest stem (greedy), or by a model that reads the sentence (prepare.model).
"""

import re
from dataclasses import dataclass

from ..languages.tr_suffixes import chains_for, stem_class
from ..quality.corpus import TOKEN
from .lexicon import Sense

HAIR = " "
APOSTROPHES = "'’"
MIN_STEM = 2


@dataclass(frozen=True)
class Split:
    stem: str
    rest: str
    senses: tuple[Sense, ...]  # what a tap on the stem opens
    analyses: tuple[str, ...]  # what the rest is ("plural + our + from (abl.)")

    @property
    def spelling(self):
        return self.stem + HAIR + self.rest


@dataclass(frozen=True)
class Target:
    """A word that needs a decision: what it opens whole, and its candidate splits,
    longest stem first."""

    word: str
    whole: tuple[Sense, ...]
    splits: tuple[Split, ...]


def words(lexicon, word):
    """The dictionary's words a tap on word reaches, without suffix-chain entries."""
    return tuple(s for s in lexicon.lookup(word) if not s.headword.startswith("-"))


def splits(lexicon, word):
    """Every candidate split of word, longest stem first."""
    found = []
    for end in range(len(word) - 1, MIN_STEM - 1, -1):
        stem, rest = word[:end], word[end:]
        if rest[0] in APOSTROPHES:
            continue  # the apostrophe stays with the name: Ali' + nin
        senses = words(lexicon, stem)
        if not senses:
            continue
        analyses = chains_for(stem_class(stem)).get(rest.lower())
        if analyses is None and stem[-1] in APOSTROPHES:
            analyses = ["suffixes of a name"]
        if analyses:
            found.append(Split(stem, rest, senses, tuple(analyses)))
    return tuple(found)


def target(lexicon, word):
    """The Target for word, or None when it is left as it is: it opens whole (and is
    not a name the apostrophe hides), or no split of it is a candidate."""
    whole = words(lexicon, word)
    if whole and not any(mark in word for mark in APOSTROPHES):
        return None
    candidates = splits(lexicon, word)
    if whole:
        # A name: split only where the part before the apostrophe opens something the
        # whole word does not (Ali' opens Ali; Ali'nin opens alının)
        whole_heads = {s.headword for s in whole}
        candidates = tuple(
            c
            for c in candidates
            if c.stem[-1] in APOSTROPHES
            and {s.headword for s in c.senses} - whole_heads
        )
    if not candidates:
        return None
    return Target(word, whole, candidates)


def greedy(targets, sentence):
    """The longest stem of each word: the baseline the model is measured against."""
    return [0 for _ in targets]


def rooted(targets, sentence):
    """The shortest stem of the word the longest stem belongs to, so the whole chain
    stays together (ol + madığını, not olmadığın + ı) while a derived word keeps its own
    stem (gözlükçü + ler, since gözlük is another word): what runs without a model."""
    choices = []
    for tgt in targets:
        heads = {sense.headword for sense in tgt.splits[0].senses}
        same = [
            i
            for i, split in enumerate(tgt.splits)
            if heads & {sense.headword for sense in split.senses}
        ]
        choices.append(same[-1])
    return choices


SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def sentences(text):
    return [s for s in SENTENCE_END.split(text) if s.strip()]


def segment_text(text, lexicon, decide):
    """text with the words decide splits written stem + hair space + rest.

    decide(targets, sentence) gets every Target of a sentence and returns, per target,
    the index of the chosen split or None to leave the word whole. Returns the text and
    a list of (word, sentence, chosen Split or None)."""
    out, report = [], []
    position = 0
    for sentence in sentences(text):
        start = text.index(sentence, position)
        out.append(text[position:start])
        position = start + len(sentence)
        out.append(_segment_sentence(sentence, lexicon, decide, report))
    out.append(text[position:])
    return "".join(out), report


def _segment_sentence(sentence, lexicon, decide, report):
    matches = list(TOKEN.finditer(sentence))
    targets = [(m, target(lexicon, m.group())) for m in matches]
    targets = [(m, t) for m, t in targets if t]
    if not targets:
        return sentence
    choices = decide([t for _, t in targets], sentence)
    pieces, last = [], 0
    for (match, tgt), choice in zip(targets, choices):
        split = tgt.splits[choice] if choice is not None else None
        report.append((tgt.word, sentence, split))
        pieces.append(sentence[last : match.start()])
        pieces.append(split.spelling if split else match.group())
        last = match.end()
    pieces.append(sentence[last:])
    return "".join(pieces)
