"""What each dictionary language does its own way. A build takes one Language, chosen by
--lang (Wiktionary's language code); the rest of the pipeline is shared.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str  # Wiktionary's code (la, grc), which Kaikki puts on every entry
    # Wiktionary's name: the dictionary's title, and the section links point to
    name: str
    index_name: str  # the lookup index: idx:entry's name and DefaultLookupIndex
    # Every spelling of a form a tap should find (Entry.get_all_forms)
    lookup_spellings: Callable[[str], list[str]]
    # The letters a form-of target is matched by when no headword is spelled like it
    # (merge.pointers.rekey_plain_roots)
    letters: Callable[[str], str]
    # Form tags marking an alternative spelling: indexed, but listed late in the popup
    alternative_tags: frozenset[str]
    # Forms made with an auxiliary ("amātus sum"), which no tap reaches; None if none
    periphrastic: str | None
    # Kaikki files participles and gerunds under "verb"; their head template says which
    pos_by_head_template: dict[str, str]
    # (spelling, tags) of the regular forms an entry's forms imply (merge.forms)
    implied_forms: Callable[[list[dict], set[str]], Iterable[tuple[str, list[str]]]]
    descendants: tuple[str, ...]  # descendant languages kept unless --descendants
    homographs: str  # words spelled alike, as markup, for the front page
    # (causes, variant) a word that opens nothing is retried with, to name why
    miss_variants: Callable[[str], Iterable[tuple[tuple[str, ...], str]]]

    @property
    def anchor(self):
        """What a link to this language's section of a Wiktionary page ends with."""
        return "#" + self.name.replace(" ", "_")


from .grc import ANCIENT_GREEK
from .la import LATIN

LANGUAGES = {language.code: language for language in (LATIN, ANCIENT_GREEK)}


def get_language(code):
    return LANGUAGES[code]
