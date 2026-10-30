"""Render stage: write entries and the front page as XHTML pages."""

import os
from pathlib import Path

from ..utils import TEMPLATES
from .cover import dictionary_cover
from .html_page import HTMLPage
from .html_renderer import HTMLRenderer
from .popup_order import rank_spellings, weigh
from .shared_labels import distinguish_shared_labels


class BookWriter:
    """Write the dictionary's pages into files_dir: entries (0000.xhtml, ...) and the
    front page."""

    def __init__(self, files_dir, language, max_page_len=5000, descendant_langs=None):
        self.files_dir = files_dir
        self.language = language
        self.descendant_langs = descendant_langs
        self.entry_pages = {}  # entry id -> its page's filename
        self.weights = {}  # entry id -> estimated frequency (popup_order)
        self.entries = HTMLPage(
            max_lines=max_page_len, output_fp_prefix=os.path.join(files_dir, "")
        )

        os.makedirs(files_dir, exist_ok=True)
        Path(files_dir, "style.css").write_bytes(
            TEMPLATES.joinpath("style.css").read_bytes()
        )
        Path(files_dir, "cover.png").write_bytes(dictionary_cover(language.name))

    def add_entry(self, entry):
        """Render entry, indexed by its headword and all its forms. Return False,
        indexing nothing, if it has no senses."""
        lines = HTMLRenderer.render_entry(entry, self.descendant_langs)
        if not lines:
            return False
        self.entry_pages[entry.id_number] = self.entries.get_filename()
        self.weights[entry.id_number] = weigh(entry)
        self.entries.add_lines(lines)
        return True

    def finish(self, dump_date, build_date, version):
        """Write the last entry page, rank the entries each spelling without accents
        reaches (popup_order), give entries that share a label one each, and write the
        front page."""
        self.entries.write()
        pages = [
            Path(self.files_dir, f"{page:04}.xhtml") for page in range(self.page_count)
        ]
        rank_spellings(pages, self.weights)
        distinguish_shared_labels(pages, self.weights)
        self.write_front(dump_date, build_date, version)

    def write_front(self, dump_date, build_date, version):
        header = TEMPLATES.joinpath("html_header.txt").read_text("utf-8").split("\n")
        footer = TEMPLATES.joinpath("html_footer.txt").read_text("utf-8").split("\n")
        body = HTMLRenderer.render_front(self.language, dump_date, build_date, version)
        Path(self.files_dir, "front.xhtml").write_text(
            "\n".join(header + body + footer), encoding="utf-8"
        )

    @property
    def page_count(self):
        """The number of entry pages written."""
        return self.entries.index
