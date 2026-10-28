"""Build a Kindle dictionary from a filtered Kaikki dump, one stage after another:

ingest (ingest.py: download and filter the dump) → merge (merge/: sort it and fold pointer
pages into their lemmas) → lexicon model (models/: Entry objects) → label resolution
(label_resolver.py: one owner per spelling, disambiguation cards) → render (render/: XHTML
pages) → compile (compiler.py: OPF package and kindling).

Entries are read from the merged dump twice, once to collect every label and once to
render, so the whole lexicon is never held in memory.
"""

import datetime
import os
from dataclasses import dataclass, field

from . import __version__
from .compiler import compile_mobi, write_opf
from .ingest import dump_date
from .label_resolver import LabelResolver
from .merge.sort import is_sorted, merge_dump
from .models.lexicon import count_lines, read_entries
from .render.book import BookWriter


@dataclass
class Build:
    output_dir: str
    files_dir: str  # the XHTML pages and OPF package kindling compiles
    dump_date: str
    build_date: str
    entry_pages: dict[int, str] = field(default_factory=dict)  # entry id -> page


def unique_directory(path):
    if not os.path.exists(path):
        return path
    base, counter = path, 1
    while os.path.exists(f"{base} ({counter})"):
        counter += 1
    return f"{base} ({counter})"


def resolve_labels(entries):
    """Give each spelling one owner, an entry or a card (see label_resolver)."""
    resolver = LabelResolver()
    for entry, size in entries:
        resolver.add(entry.id_number, entry.head_word, entry.all_forms, size, entry.pos)
    return resolver, resolver.resolve()


def build_dictionary(
    dump,
    lang_code,
    kindling,
    descendant_langs=None,
    resort=False,
    limit=None,
    max_page_len=5000,
):
    """Build outputs/KindleDictionary-<lang_code> (or a free name beside it) from dump, a
    filtered dump or one merge_dump already sorted. limit caps the number of entries."""
    build = Build(
        output_dir=unique_directory(f"outputs/KindleDictionary-{lang_code}"),
        files_dir="",
        dump_date=dump_date(dump),  # read before dump becomes the sorted file
        build_date=datetime.date.today().isoformat(),
    )
    build.files_dir = os.path.join(build.output_dir, "files")

    if not is_sorted(dump):
        dump = merge_dump(dump, lang_code, force=resort).path
    total = count_lines(dump)

    resolver, cards = resolve_labels(
        read_entries(dump, limit, "Indexing labels", total)
    )

    writer = BookWriter(build.files_dir, cards, max_page_len, descendant_langs)
    for entry, _size in read_entries(dump, limit, "Building", total):
        orth, iforms = resolver.entry_labels(
            entry.id_number, entry.head_word, sorted(entry.all_forms)
        )
        writer.add_entry(entry, orth, iforms)
    writer.finish(build.dump_date, build.build_date, __version__)
    build.entry_pages = writer.entry_pages

    write_opf(
        build.files_dir,
        writer.page_counts,
        build.dump_date,
        build.build_date,
        __version__,
    )
    compile_mobi(
        kindling, build.files_dir, build.output_dir, f"{lang_code}-wiktionary.mobi"
    )
    return build
