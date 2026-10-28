"""Decide which entry or disambiguation card owns each lookup label.

A tapped word reaches every label with the same Kindle weights (see utils.kindle_fold), and
the device opens the label spelled exactly like the word, else the first one equal to it
ignoring case, else whichever the index stores first. So that every tap opens one predictable
thing, each exact spelling gets one owner:

- A spelling only one entry has stays on that entry, so a macronized tap ("lātum") opens it.
- When several entries have labels that differ only by accents, case or æ/œ, a card owns
  their unmacronized spellings ("latum", "Latum") and lists all those entries.
- A spelling several entries share exactly (same macrons, different lemmas) also goes to a
  card listing just those entries.
- Labels that differ only by punctuation are told apart by an exact tap, so "ad" and "a.d."
  share no card. Where a tap reaches several entries but only one has a given spelling, that
  entry also gets the spelling unmacronized ("non" on nōn, beside the abbreviation Non.), and
  where every spelling has punctuation (M., M'), a card owns the bare one ("M").

A card lists the entries Wiktionary says most about first (their size without inflection
tables), a rough stand-in for how common a word is, and proper names last.

Entries lose the labels a card takes. An entry whose headword is taken keeps a headword label
numbered by its place on the card ("latus¹"); the superscript has its own weight, so no tap
reaches it, and the card links to the entry instead.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from .utils import KINDLE_LIGATURES, kindle_fold, normalize

SUPERSCRIPTS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
UNLIGATE = str.maketrans(KINDLE_LIGATURES)
LIGATE = (("ae", "æ"), ("oe", "œ"), ("Ae", "Æ"), ("AE", "Æ"), ("Oe", "Œ"), ("OE", "Œ"))


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
        self.ranks = {}  # entry id -> sort key for listing it on a card
        self.cards = []
        self.card_of = {}  # label taken by a card -> that card
        self.extra = defaultdict(
            list
        )  # entry id -> unmacronized spellings it also gets

    def add(self, entry_id, head_word, labels, size=0, pos=None):
        """Index an entry's labels; a larger size lists it earlier on cards."""
        self.ranks[entry_id] = (pos == "name", -size, entry_id)
        for label in dict.fromkeys([head_word, *labels]):
            self.owners[label].append(entry_id)

    def resolve(self):
        by_fold = defaultdict(list)
        for label in self.owners:
            by_fold[kindle_fold(label)].append(label)

        for fold in sorted(by_fold):
            labels = sorted(by_fold[fold])
            if len({i for lb in labels for i in self.owners[lb]}) < 2:
                continue

            by_spelling = defaultdict(list)
            for label in labels:
                by_spelling[spelling_key(label)].append(label)
            for key in sorted(by_spelling):
                self._resolve_spelling(by_spelling[key])
            if not any(key == _bare(key) for key in by_spelling):
                self._add_card({_bare(lb) for lb in _plain_spellings(labels)}, labels)
        self._merge_variant_cards()
        return self.cards

    def _merge_variant_cards(self):
        """Merge cards that list the same entries and differ only by u for v or j for i
        (conservandi, conseruandi): one card takes all their labels, headed by the spelling
        Wiktionary uses."""
        merged = {}
        for card in self.cards:
            key = (tuple(card.owners), _variant_key(card.labels[0]))
            first = merged.setdefault(key, card)
            if first is card:
                continue
            first.labels = sorted({*first.labels, *card.labels}, key=_wiktionary_first)
            for owner, labels in card.reached.items():
                first.reached[owner] = list(
                    dict.fromkeys(first.reached[owner] + labels)
                )
        self.cards = list(merged.values())
        for number, card in enumerate(self.cards, 1):
            card.id_number = number
            for label in card.labels:
                self.card_of[label] = card

    def _resolve_spelling(self, labels):
        """Give one owner to labels that differ only by accents, case or æ/œ."""
        reached = list(dict.fromkeys(i for lb in labels for i in self.owners[lb]))
        plain = _plain_spellings(labels)
        if len(reached) == 1:
            self.extra[reached[0]].extend(sorted(plain - set(self.owners)))
            return

        # Owner set -> (labels the card takes, labels by which it reaches its owners)
        cards = defaultdict(lambda: (set(), []))
        cards[frozenset(reached)][0].update(plain)
        cards[frozenset(reached)][1].extend(labels)
        for label in labels:
            if label not in plain and len(self.owners[label]) > 1:
                cards[frozenset(self.owners[label])][0].add(label)
                cards[frozenset(self.owners[label])][1].append(label)
        for card_labels, sources in cards.values():
            self._add_card(card_labels, sources)

    def _add_card(self, labels, sources):
        """Create a card owning labels and listing every owner of sources."""
        owners = {i for lb in sources for i in self.owners[lb]}
        card = Card(
            sorted(labels, key=_lowercase_first), sorted(owners, key=self.ranks.get)
        )
        card.id_number = len(self.cards) + 1
        for owner in card.owners:
            card.reached[owner] = []
        for label in dict.fromkeys(sources):
            for owner in self.owners[label]:
                card.reached[owner].append(label)
        for label in card.labels:
            self.card_of[label] = card
        self.cards.append(card)

    def entry_labels(self, entry_id, head_word, labels):
        """Return (headword label, other labels) an entry is indexed by after resolve()."""
        orth = head_word
        if card := self.card_of.get(head_word):
            number = card.owners.index(entry_id) + 1
            orth = head_word + str(number).translate(SUPERSCRIPTS)
        others = [lb for lb in labels if lb != head_word and lb not in self.card_of]
        return orth, others + self.extra.get(entry_id, [])


def spelling_key(label):
    """Labels with the same key differ only by accents, case or æ/œ: an unmacronized tap
    cannot tell them apart."""
    return normalize(label, lowercase=True).translate(UNLIGATE)


def _plain_spellings(labels):
    """Unmacronized spellings of labels, each also with and without æ/œ, so a tap in a text
    that writes Ægypti or Aegypti lands on the card by spelling, not by index order."""
    plain = set()
    for label in labels:
        spelling = normalize(label)
        if kindle_fold(spelling) != kindle_fold(label):
            # normalize() also dropped a mark the device weighs (aͣ): that is another word
            plain.add(label)
            continue
        ligated = spelling
        for pair, ligature in LIGATE:
            ligated = ligated.replace(pair, ligature)
        plain.update([spelling, spelling.translate(UNLIGATE), ligated])
    return plain


def _bare(spelling):
    """spelling without the characters the device ignores (punctuation)."""
    return "".join(char for char in spelling if kindle_fold(char))


def _lowercase_first(label):
    return label != label.lower(), label


def _wiktionary_first(label):
    """Lowercase first, then the spelling with the fewest u and j (Wiktionary writes v for
    consonantal u and never j)."""
    return label != label.lower(), sum(char in "uUjJ" for char in label), label


def _variant_key(label):
    return kindle_fold(label).replace("j", "i").replace("v", "u")
