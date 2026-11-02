# How Kindle lookup works

Amazon documents almost none of how a Kindle finds a word in a dictionary, and the design of this project rests on it. This note collects what is known: from the [kindling README](https://github.com/ciscoriordan/kindling) and source (measured there on a Kindle 4, Paperwhite 4 and Paperwhite 5), from [KDP: Creating Dictionaries](https://kdp.amazon.com/en_US/help/topic/G2HXJS944GL88DNV), and from this project's own tests on a device. Points not yet checked on a device are marked as such.

## Every language

- **A long press stops at a hair space (U+200A), and at no zero-width or other thin space.** `virum` + U+200A + `que` selects `virum` alone, and a press on `que` selects `que`. With a zero-width space (U+200B) or another thin space in its place, the selection runs on through it, and since those characters weigh nothing in matching, the press is looked up as `virumque`. A hair space is a real space character: narrow but not invisible, and a place where a line may break. It is the only way a book can split a word for lookup.
- **Lookup matches the whole selected word.** There is no stemming and no prefix match, so every form a text prints must be a label of some entry.
- **A pressed word reaches every label with the same weights.** Punctuation weighs nothing. How letters weigh depends on the script (below).
- **The popup lists every entry reached.** Of those, the one spelled exactly like the pressed word comes first; else the first equal to it ignoring case; else, apart from some prefix rules, the first in index order. The reader swipes to the rest. Links do not work in the popup.
- **kindling stores one index record per label string.** When several entries share a label (`et` the conjunction and `et` the adverb), only one would be reached, so the build gives the others a soft hyphen, which weighs nothing, after the first letter (`render/shared_labels.py`).
- **The popup applies no stylesheet**, and kindling strips `class` attributes, so entries use `<b>` and `<i>` rather than CSS.
- `kindling-cli lookup <dict.mobi> <word>` predicts what a Paperwhite 5 opens, exits 1 on a miss, and reports ties and labels that index order hides. `scripts/check_lookups.py` and the coverage reports use it.
- KDP lists a copyright page as required content. Wiktionary's text is CC BY-SA, so each dictionary opens with an attribution and license page.

## Latin

- **Case and accents do not count**, macrons included: Latin letters weigh as their lowercase base letter, and ß, æ and œ as ss, ae and oe. A separate combining mark (the breve in ā̆) counts as itself.
- So the device needs no unmacronized or lowercase labels to match. They matter only for order: an exact spelling decides which entry the popup lists first, so the likeliest entry of each ambiguous spelling gets the unmacronized label (`render/popup_order.py`). Wiktionary has no word frequencies, so the build estimates likelihood from how much Wiktionary says about each word; that is why *non* lists *nōn* before *nōnae*.
- *u*/*v* and *i*/*j* do count, so the build adds those spellings itself.
- Wiktionary's conventions: page titles without macrons, headwords with them, ā̆ for a disputed length, v for consonantal u, no j, and no æ or œ in headwords. Kaikki's form-of targets keep their macrons.

## Ancient Greek

From kindling's documentation and source; not all of it has been checked on a device yet.

- **The device folds nothing in Greek.** Greek letters and combining marks weigh as themselves, so case and accents count: `Κάτι` does not find `κάτι`. Every spelling a text prints must be a label, so the build adds the spellings without length marks, with a grave for a final acute, and capitalized.
- A Greek book ignores case only when choosing among labels that already weigh the same, so it does not rescue a capitalized press.
- **Code points count, not canonical equivalence.** Oxia `ά` (U+1F71) and tonos `ά` (U+03AC) are different characters to the device, and a decomposed letter is not a precomposed one.
- The right single quotation mark (U+2019) and the modifier apostrophe (U+02BC) used for elision weigh nothing; the Greek koronis `᾽` (U+1FBD) does not. Whether the selection takes in an elision mark at all is still to check on a device.

## Turkish

- **The device folds Turkish letters.** `ı`, `İ`, `I` and `i` weigh the same, as do ş/s, ğ/g, ç/c, ö/o, ü/u and â/î/û, so no case or accent variants are needed. The cost runs the other way: different words meet (`katlı` reaches `katli`, from *katil*).
- A Turkish book tells `I` from `i` when choosing among labels with the same weights.
- **An apostrophe weighs nothing**, so a name with its suffixes (`Ali'nin`) is looked up as `alinin` and reaches whatever common word folds the same, unless the name's own table lists the form. Whether a long press stops at the apostrophe is still to check on a device.
- Wiktionary's tables list a noun's case, number and possessive forms and a verb's tenses, moods and persons, but texts add the copula to nouns (`evdeydi`), `-ki`, `-le` and derivations no table lists. Past what the build generates, a book is split with hair spaces by `prepare-book` (see the [developer guide](DEVELOPING.md#preparing-books-turkish)).
