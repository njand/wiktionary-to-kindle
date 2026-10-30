"""Build a Kindle dictionary from a filtered Kaikki dump, one stage after another:

ingest (ingest.py: download and filter the dump) → merge (merge/: sort it and fold pointer
pages into their lemmas) → lexicon model (models/: Entry objects) → render (render/: XHTML
pages) → compile (compiler.py: OPF package and kindling) → optionally a StarDict bundle
(stardict.py).

Each entry is indexed by all of its own spellings, and entries share labels freely: a tap
that reaches several entries (latus, lātus) shows each of them in the popup, the one
spelled like the tap first. Entries are streamed from the merged dump, so the whole
lexicon is never held in memory.
"""

import datetime
import os
from dataclasses import dataclass, field

from . import __version__
from .compiler import compile_mobi, write_opf
from .ingest import dump_date
from .merge.sort import is_sorted, merge_dump
from .models.lexicon import count_lines, read_entries
from .render.book import BookWriter
from .stardict import export_stardict

# The .ifo has no license field; by convention it goes in the description
STARDICT_DESCRIPTION = (
    "{name}-English dictionary from Wiktionary data of {dump_date}, built with "
    "wiktionary-to-kindle {version}.<br>Text by Wiktionary contributors "
    "(https://en.wiktionary.org/), extracted by Kaikki.org and wiktextract; licensed "
    "under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)."
)


@dataclass
class Build:
    output_dir: str
    files_dir: str  # the XHTML pages and OPF package kindling compiles
    dump_date: str
    build_date: str
    entry_pages: dict[int, str] = field(default_factory=dict)  # entry id -> page
    stardict_zip: str | None = None


def unique_directory(path):
    if not os.path.exists(path):
        return path
    base, counter = path, 1
    while os.path.exists(f"{base} ({counter})"):
        counter += 1
    return f"{base} ({counter})"


def build_dictionary(
    dump,
    language,
    kindling,
    descendant_langs=None,
    resort=False,
    limit=None,
    max_page_len=5000,
    stardict=False,
):
    """Build outputs/KindleDictionary-<code> (or a free name beside it) from dump, a
    filtered dump or one merge_dump already sorted, for language (a Language). limit caps
    the number of entries; descendant_langs defaults to the language's; stardict also
    writes <code>-wiktionary-stardict.zip."""
    if descendant_langs is None:
        descendant_langs = list(language.descendants)
    build = Build(
        output_dir=unique_directory(f"outputs/KindleDictionary-{language.code}"),
        files_dir="",
        dump_date=dump_date(dump),  # read before dump becomes the sorted file
        build_date=datetime.date.today().isoformat(),
    )
    build.files_dir = os.path.join(build.output_dir, "files")

    if not is_sorted(dump):
        dump = merge_dump(dump, language, force=resort).path
    total = count_lines(dump)

    writer = BookWriter(build.files_dir, language, max_page_len, descendant_langs)
    for entry in read_entries(dump, language, limit, "Building", total):
        writer.add_entry(entry)
    writer.finish(build.dump_date, build.build_date, __version__)
    build.entry_pages = writer.entry_pages

    write_opf(
        build.files_dir,
        language,
        writer.page_count,
        build.dump_date,
        build.build_date,
        __version__,
    )
    compile_mobi(
        kindling,
        build.files_dir,
        build.output_dir,
        f"{language.code}-wiktionary.mobi",
    )
    if stardict:
        build.stardict_zip = str(
            export_stardict(
                kindling,
                build.files_dir,
                os.path.join(
                    build.output_dir, "stardict", f"{language.code}-wiktionary"
                ),
                STARDICT_DESCRIPTION.format(
                    name=language.name, dump_date=build.dump_date, version=__version__
                ),
            )
        )
    return build
