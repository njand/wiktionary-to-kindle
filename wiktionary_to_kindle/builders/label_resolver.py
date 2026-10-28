"""Decide which entry or disambiguation card owns each lookup label.

A tapped word reaches every label with the same Kindle weights (see utils.kindle_fold), and
the device opens the label spelled exactly like the word, else the first one equal to it
ignoring case, else whichever the index stores first. So that every tap opens one predictable
thing, each exact spelling gets one owner:

- A spelling only one entry has stays on that entry, so a macronized tap ("lātum") opens it.
- When a folded key reaches several entries, a card owns the key's unmacronized spellings
  ("latum") and lists every entry the key reaches.
- A spelling several entries share exactly (same macrons, different lemmas) also goes to a
  card listing just those entries.

Entries lose the labels a card takes. An entry whose headword is taken keeps a headword label
numbered by its place on the card ("latus¹"); the superscript has its own weight, so no tap
reaches it, and the card links to the entry instead.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from ..utils import kindle_fold, normalize

SUPERSCRIPTS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


@dataclass
class Card:
    labels: list[str]  # the first is shown as the card's headword
    owners: list[int]  # entry ids, in the order listed
    id_number: int = 0
    # Each owner's labels that this card took, to show which of its forms was tapped
    reached: dict[int, list[str]] = field(default_factory=dict)


class LabelResolver:
    def __init__(self):
        self.owners = defaultdict(list)  # exact label -> entry ids, in dictionary order
        self.head_words = {}  # entry id -> headword label
        self.cards = []
        self.card_of = {}  # label taken by a card -> that card

    def add(self, entry_id, head_word, labels):
        self.head_words[entry_id] = head_word
        for label in dict.fromkeys([head_word, *labels]):
            self.owners[label].append(entry_id)

    def resolve(self):
        by_fold = defaultdict(list)
        for label in self.owners:
            by_fold[kindle_fold(label)].append(label)

        for fold in sorted(by_fold):
            labels = sorted(by_fold[fold])
            reached = list(dict.fromkeys(i for lb in labels for i in self.owners[lb]))
            if len(reached) < 2:
                continue

            # Owner set -> labels a card with exactly those owners takes
            cards = defaultdict(list)
            plain = sorted({normalize(lb) for lb in labels}, key=_lowercase_first)
            cards[frozenset(reached)].extend(plain)
            for label in labels:
                if label not in plain and len(self.owners[label]) > 1:
                    cards[frozenset(self.owners[label])].append(label)

            for owner_set, card_labels in cards.items():
                card = Card(card_labels, self._order(owner_set, card_labels[0]))
                card.id_number = len(self.cards) + 1
                for owner in card.owners:
                    card.reached[owner] = []
                for label in card_labels:
                    self.card_of[label] = card
                    for owner in self.owners.get(label, []):
                        card.reached[owner].append(label)
                self.cards.append(card)
        return self.cards

    def _order(self, owner_set, label):
        """Entries whose headword is spelled like the card's label first, then those whose
        headword differs only by accents or case, then dictionary order."""
        plain = normalize(label, lowercase=True)

        def key(entry_id):
            head = self.head_words[entry_id]
            return head != label, normalize(head, lowercase=True) != plain, entry_id

        return sorted(owner_set, key=key)

    def entry_labels(self, entry_id, head_word, labels):
        """Return (headword label, other labels) left to an entry after resolve()."""
        orth = head_word
        if card := self.card_of.get(head_word):
            number = card.owners.index(entry_id) + 1
            orth = head_word + str(number).translate(SUPERSCRIPTS)
        others = [lb for lb in labels if lb != head_word and lb not in self.card_of]
        return orth, others


def _lowercase_first(label):
    return label != label.lower(), label
