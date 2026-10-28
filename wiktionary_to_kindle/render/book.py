"""Render stage: write entries, disambiguation cards and the front page as XHTML pages."""

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..utils import TEMPLATES, lookup_spellings
from .html_page import HTMLPage
from .html_renderer import HTMLRenderer, format_gloss


@dataclass
class CardRow:
    """One entry as a disambiguation card lists it."""

    head: str
    pos: str | None
    parses: list[str]
    gloss: str
    id: int
    page: str = ""


def card_rows(entry, cards):
    """List entry on each of its cards: its headword, and the parses of the forms that
    were tapped. A verb can be on hundreds of cards, so its forms are indexed once."""
    inflections = sorted(entry.inflected_forms.items(), key=lambda kv: kv[1])
    forms_of = defaultdict(list)  # label -> indexes into inflections
    for i, (form, _inflection) in enumerate(inflections):
        for label in lookup_spellings(form):
            forms_of[label].append(i)
    parses_of = [
        [str(tag) for tag in sorted(inflection.morph_tags)]
        for _form, inflection in inflections
    ]
    block, header = entry.valid_pairs()[0]
    gloss = format_gloss(next(iter(block.senses.values())))

    rows = {}
    for card in cards:
        reached = card.reached[entry.id_number]
        indexes = sorted({i for label in reached for i in forms_of.get(label, [])})
        parses = [p for i in indexes for p in parses_of[i] if p]
        rows[card.id_number] = CardRow(
            head=header.head_word,
            pos=entry.pos,
            parses=list(dict.fromkeys(parses)),
            gloss=gloss,
            id=entry.id_number,
        )
    return rows


class BookWriter:
    """Write the dictionary's pages into files_dir: entries (0000.xhtml, ...), then cards
    (card-0000.xhtml, ...), each card listing the entries its labels reach."""

    def __init__(self, files_dir, cards, max_page_len=5000, descendant_langs=None):
        self.files_dir = files_dir
        self.cards = cards
        self.descendant_langs = descendant_langs
        self.entry_pages = {}  # entry id -> its page's filename
        self.entries = HTMLPage(
            max_lines=max_page_len, output_fp_prefix=os.path.join(files_dir, "")
        )
        self.card_pages = HTMLPage(
            max_lines=max_page_len, output_fp_prefix=os.path.join(files_dir, "card-")
        )
        self.cards_of = defaultdict(list)
        for card in cards:
            for owner in card.owners:
                self.cards_of[owner].append(card)
        self.rows = defaultdict(dict)  # card id -> entry id -> CardRow

        os.makedirs(files_dir, exist_ok=True)
        for name in ("style.css", "cover.png"):
            data = TEMPLATES.joinpath(name).read_bytes()
            Path(files_dir, name).write_bytes(data)

    def add_entry(self, entry, orth, iforms):
        """Render entry indexed by orth and iforms, and remember its row on each of its
        cards. Return False, indexing nothing, if it has no senses."""
        if entry_cards := self.cards_of.pop(entry.id_number, []):
            for card_id, row in card_rows(entry, entry_cards).items():
                self.rows[card_id][entry.id_number] = row

        lines = HTMLRenderer.render_entry(
            entry, self.descendant_langs, orth=orth, iforms=iforms
        )
        if not lines:
            return False
        self.entry_pages[entry.id_number] = self.entries.get_filename()
        self.entries.add_lines(lines)
        return True

    def finish(self, dump_date, build_date, version):
        """Write the cards, now that every entry's page is known, and the front page."""
        for card in self.cards:
            rows = []
            for owner in card.owners:
                row = self.rows[card.id_number][owner]
                row.page = self.entry_pages.get(owner, "")
                rows.append(row)
            self.card_pages.add_lines(HTMLRenderer.render_card(card, rows))

        self.entries.write()
        self.card_pages.write()
        self.write_front(dump_date, build_date, version)

    def write_front(self, dump_date, build_date, version):
        header = TEMPLATES.joinpath("html_header.txt").read_text("utf-8").split("\n")
        footer = TEMPLATES.joinpath("html_footer.txt").read_text("utf-8").split("\n")
        body = HTMLRenderer.render_front(dump_date, build_date, version)
        Path(self.files_dir, "front.xhtml").write_text(
            "\n".join(header + body + footer), encoding="utf-8"
        )

    @property
    def page_counts(self):
        """The number of entry pages and of card pages written."""
        return self.entries.index, self.card_pages.index
