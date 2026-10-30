# Handoff: Latin words the Kindle dictionary misses in a real book

From e-liber to the agent working on wiktionary-to-kindle. Written 2026-10-30.

e-liber now simulates a long press on every word of a built book, using this project's own model:
`read_entries`, `build_index`, `resolve` and `miss_cause`, plus the first-entry rule from the handoff. The
book is Barclay's *Argenis* I–II (54,152 words, fully macronized, j/v, enclitics split by U+200A). The
dictionary is `outputs/KindleDictionary-la (19)`, built 2026-10-30 from Wiktionary data of 2026-10-25. 96.2% of
the words open an entry. This file lists every miss that isn't one of Barclay's invented names, sorted by what
would fix it.

## First: most of these aren't templates the build fails to expand

I checked whether Wiktionary has each missing form in two ways:

- e-liber's Wiktionary form data (`lrl macron`, source W): **none of the 179 missed forms checked is a W
  form.** Some are in the Macronizer word list (M) only.
- en.wiktionary.org by hand:
  - `serēnus` names no comparative or superlative, in its headline or its declension table.
  - `sanciō` conjugates only `sānxī`, so there is no `sancīvit`.
  - `Anaximander` has no declension table.
  - `mapālia` is declined in the 2nd declension, so `mapāliīs`, not Barclay's `mapālibus`.
  - `Phrygius` and `Tartareus` have no page at all.

So the build indexes what Wiktionary gives. A few real expansion bugs remain (section A). Most misses
need forms **generated** where Wiktionary implies them but doesn't list them (section B), which the
dictionary's front page already allows ("some regular forms that Wiktionary implies are generated"). The rest
are words Wiktionary doesn't have (section C).

`×n` is the number of times a form occurs in the book.

## A. Data Wiktionary has that the build doesn't index (bugs)

1. **Enclitic halves open the wrong entry, or nothing.** In a split word (`virum` + U+200A + `que`), the half
   after the hair space is a lookup of its own:
   - `que` opens quī / quis.
   - `ne` opens nē / neō.
   - `ve` opens nothing (×45 in Argenis).

   Wiktionary has Latin entries `-que`, `-ne` and `-ve` (`-ve` checked: a conjunction and a suffix). Indexing
   those three, with labels `que`, `ne` and `ve`
   shown first, would make every split word in e-liber's books open the right entries on both halves. This
   isn't indexing enclitic *compounds* (`virumque`), which stays out by design.
2. **An alternative perfect stem is indexed only in its first person.** `percurrō`'s page notes "the perfect
   active indicative can be written as percurrī". The build gives `percurrī` a label, but not its other
   forms, so `percurrērunt` misses.
3. **An alternative spelling is indexed only as its headword form, not inflected.** The entry carries the
   variant as a label but none of its case or tense forms:
   - `Cēphīsus`: `Cēphissus` opens, but `Cēphissum` (×1) and `Cēphissī` don't.
   - `āvehō`: `abvehō` is a label, but `abvēxisse` (×1) and `abvēxēre` (×1) aren't.
   - `catulus`: `catula` is a label, but `catulae` (×1) isn't.
4. **A label without its macron:** `officiōsus` has the adverb as `officiōse`, not `officiōsē`. It still opens,
   since macrons weigh nothing, but the label is misspelt.

## B. Regular forms Wiktionary implies but doesn't list (generate)

1. **Comparatives and superlatives of adjectives.** These are generated only where Wiktionary's headline
   names them: `fortis` → fortior, fortissimus open; `blandus` names only `blandior`, so `blandissimus` misses;
   `serēnus` names neither. In every case below the positive is in the dictionary:

   | Missed (×n) | Positive in the dictionary |
   | --- | --- |
   | serēnissima | serēnus |
   | praesentiōra, praesentiōrī ×4, praesentissimī, praesentissimō ×2 | praesēns (participle) |
   | pervicācius, pervicācissimum, pervicācissima ×2 | pervicāx |
   | blandissimus | blandus |
   | perīculōsiōrēs ×2 | perīculōsus |
   | convenientissimās ×2 | conveniēns (participle) |
   | meritissimā ×2 | meritus (participle) |
   | efficācissimā | efficāx |
   | addictior | addictus |
   | intūtissimā ×2 | intūtus |
   | ingrātior | ingrātus |
   | tranquilliōra | tranquillus |
   | sagācior | sagāx |
   | pavidius, pavidissimā | pavidus |
   | cōnsultissimum ×3, cōnsultiōribus | cōnsultus |
   | cōmptior | cōmptus |
   | sēcrētissimam | sēcrētus (participle) |
   | auspicātissimē (adverb) | auspicātus |
   | placidissimā | placidus |
   | irreligiōsissima | irreligiōsus |
   | perplexius | perplexus |
   | īnspērātissimā | īnspērātus |
   | fervidiōra | fervidus |
   | lūculentius | lūculentus |
   | reverentior | reverēns |
   | laudābiliōrī | laudābilis |
   | citātior ×2 | citātus (participle) |
   | prōvectiōrum | prōvectus (participle) |

   - **Forms to generate:**
     - Regular: *-ior, -ius* plus the 3rd-declension forms, and *-issimus* with its forms and adverb
       *-issimē*.
     - *-errimus* for adjectives in *-er*, and *-illimus* for the six in *-ilis*.
     - The adverb's comparative *-ius*.
   - **Which entries:** participles that Wiktionary also treats as adjectives belong in. The list shows
     readers meet them.
   - **Collisions:** check before adding. `blandior` is also a verb; a generated label should rank after an
     entry Wiktionary itself spells that way.
2. **Syncopated perfects.** `amō` has `amāsse` and `amārunt` because its table lists them. `adventō` lacks
   `adventāsse` (×2) because its table doesn't. Generating *-āsse, -āssem, -ārunt, -āstī* (and *-īsse,
   -iit* for the 4th conjugation) from every *-āv-*/*-īv-* perfect would cover these.
3. **Greek declension forms** on entries that exist:
   - `Ācis` → `Ācim` ×2.
   - `iaspis` → `iaspida`.
   - `cyclōps` → `Cyclōpas`.
   - `Philoctētēs` → `Philoctētem`.
   - `Typhōeus` → `Typhōeum` ×3, `Typhōem`.

   The accusatives *-im*, *-a*, *-as*, and Latinized *-em* / *-eum*.
4. **Proper nouns with no declension table** get only their headword:
   - `Anaximander` → `Anaximandrum` ×2 missed.
   - `Lȳdus` has the singular but no plural → `Lȳdōrum`.

   The ending and gender are enough to decline most of these.
5. **Genitive plural in -um of 3rd-declension participles** (poetic and late): `prūdentum` ×3, `potentum`,
   `rēgnantum` ×2, `vēnantum` ×2. Optional; tables give only *-ium*.
6. **Variant perfect stems that Wiktionary doesn't give.** These are spellings in Barclay's text; e-liber
   could instead normalize them in the book. Ask the user which side should handle them:
   - `retulērunt`, `retulistī`, `retulerant`, `Retuleris` ×3: `referō`, perfect rettulī. Single *t*.
   - `abfuerint`, `abfuisset` ×2, `abfuissent`: `absum`, perfect āfuī. *abfuī*.
   - `sancīvit`: `sanciō`, perfect sānxī.
   - `sarcīverit`: `sarciō`, perfect sarsī.
   - `fulcissent` ×2: `fulciō`, perfect fulsī.
   - `exsiliit` ×6, `Exiliēre`: `exsiliō`, perfect exsiluī.
   - `supervēxit`: Wiktionary has only the deponent `supervehor`.
   - `adōrsus`: `adorior`, participle adortus.
7. **Spelling variants of lemmas in the dictionary.** These could be rule-made aliases (ex/exs,
   assimilated prefixes, ae/e, y/i, o/u, single/double consonant), with a collision check. Or e-liber can
   normalize; again, the user's call:

   | Missed | Dictionary has |
   | --- | --- |
   | excindere | exscindō |
   | exūdant, exūdantis | exsūdō |
   | aggemēns, aggemendum | adgemō |
   | laevigantur ×2 | levigō |
   | inclytus ×2, inclytī, inclyta | inclitus |
   | adolēscentiae | adulēscentia |
   | coraliōrum | corallium |
   | Tibrī, Tibris | Tiberis, Thybris |
   | Ennam ×3 | Henna |
   | Brutiīs | Bruttius |
   | tōphōs | tōfus |

## C. Not in Wiktionary at all (no fix here; e-liber gives these a note)

Common words and rare words (W knows none of them; Lewis & Short has most):

> inassuētus, octuennis, undiquāque, undequāque, violābilis, receptātrīx, exsaevīre, sulphurātus,
> rescīre (resciō), perparcere, capillitium, licitārī, mediusfidius, epitȳrum, prīdiānus, exermis, tūreus,
> effictim, saevitiēs, tūtēlāris, sēmisōpītus, cōnfragus, rhododaphnē, anancaeus, praestīgiātor, indōnātus,
> inexplētus, inexplōrātus, pernīcitās, ascīticius / adscīticius, scaphula, sollicitātor, pervastāre,
> noxiōsus, dīrigēscere (`Diriguit` ×2), intumēre (`Intumet`), plūsquam ×5, tuōpte ×2

Classical names and name adjectives that readers of Latin poetry meet. W knows none of them, and
`Phrygius` and `Tartareus` have no en.wiktionary page; I didn't open a page for the others. Barclay's
invented names are left out.

> Pallas, -adis (`Palladis` ×9, `Palladī` ×7, `Palladem` ×4, `Pallade`; the dictionary has only *palla* and
> *pallās*), Erīnys / Erīnnys, Ixīōn, Tartareus, Enceladus, Phrygius, Lȳdius, Syrācūsānus, Erycīna,
> Isthmicus, Arēopagus, Delphicus, Eleusīnius, Pentheus, Erichthonius, Trītōnia, Sicelis, Sīcanius,
> Sīdōnius, Aetnaeus, Catinēnsis, Memphīticus, Pharius, Dēlia, Dictynna, Oebalius, Lemniacus, Halirrhothius,
> Cercyōn, Cōcalus, Thargēliōn, Ōgygius, Pandīonius, Chāonius, Epipolae, Ērigonē (has *Erigone* unmarked
> only), Meleager, Enyālius, Medicēī

`Pallas, -adis` (the goddess) is the one that matters most: nine taps on `Palladis` open nothing.

## Not for wiktionary-to-kindle

- e-liber writes citation forms with a prefix hyphen (`dē-ficere`) on its notes and vocabulary pages, so those
  look up in halves. That's e-liber's to fix.
- Barclay's invented names (Poliarchus, Argenis, Meleander…) miss by nature.

## How to reproduce

From e-liber: `uv run eliber lookup barclay-argenis` writes `build/barclay-argenis/lookup.txt`, which lists every
miss with its count and first place. The dictionary is chosen as the newest `outputs/KindleDictionary-la*`, and
its build date is printed at the top. After a fix here, rebuilding Latin and rerunning that command shows what
changed.
