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
    # The spelling an entry is filed and labelled under, from its first models.Header: the
    # head line's (Latin: macronized, which form-of targets name) or the page title's
    headword: Callable[[object], str]
    # Every spelling of a form a tap should find (Entry.get_all_forms)
    lookup_spellings: Callable[[str], list[str]]
    # Whether a form's spellings also get capitalized ones, by the entry's part of speech
    # and whether the form is a headword; the device folds case only in Latin letters
    capitalizes: Callable[[str | None, bool], bool]
    # The letters a form-of target is matched by when no headword is spelled like it
    # (merge.pointers.rekey_plain_roots)
    letters: Callable[[str], str]
    # Form tags marking an alternative spelling: indexed, but listed late in the popup
    alternative_tags: frozenset[str]
    # Whether a table form (Kaikki's form dict) is no spelling of its entry: made with an
    # auxiliary ("amātus sum", the εἶεν of "λελυμένοι εἶεν"), or a romanization; or one
    # Kaikki could not tag (unrecognized), which Latin and Greek skip and Turkish keeps
    skips_form: Callable[[dict], bool]
    # Kaikki files participles and gerunds under "verb"; their head template says which
    pos_by_head_template: dict[str, str]
    # (spelling, tags) of the regular forms an entry's forms imply (merge.forms)
    implied_forms: Callable[[list[dict], set[str]], Iterable[tuple[str, list[str]]]]
    # The head line after the headword, made ready for render.headline: (text, pos) -> text
    head_line: Callable[[str, str | None], str]
    # How the head line's genders are shown: m -> m. (Latin), m -> ὁ (Greek)
    genders: dict[str, str]
    descendants: tuple[str, ...]  # descendant languages kept unless --descendants
    homographs: str  # words spelled alike, as markup, for the front page
    # (causes, variant) a word that opens nothing is retried with, to name why
    miss_variants: Callable[[str], Iterable[tuple[tuple[str, ...], str]]]

    @property
    def anchor(self):
        """What a link to this language's section of a Wiktionary page ends with."""
        return "#" + self.name.replace(" ", "_")


def unrecognized(form):
    """Whether Kaikki could not tag a table form (it tags it error-unrecognized-form): in
    Latin and Greek tables mostly notes, in Turkish ones converbs and copula forms."""
    return "error-unrecognized-form" in form.get("tags", [])


from .grc import ANCIENT_GREEK
from .la import LATIN
from .tr import TURKISH

LANGUAGES = {language.code: language for language in (LATIN, ANCIENT_GREEK, TURKISH)}


def get_language(code):
    return LANGUAGES[code]
