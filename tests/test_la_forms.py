"""Latin forms the build generates where Wiktionary implies them (languages/la_*.py):
comparison and adverbs, syncopated and other spellings, Greek and name declensions."""

import json

from wiktionary_to_kindle.languages import LATIN
from wiktionary_to_kindle.languages.la import implied_forms
from wiktionary_to_kindle.languages.la_comparison import comparison
from wiktionary_to_kindle.languages.la_spellings import (
    respelled,
    syncopated,
)
from wiktionary_to_kindle.merge.sort import merge_dump
from wiktionary_to_kindle.models.entry import Entry

from .test_forms import form, spellings
from .test_sort_merge import find, lemma


def page(expansion, template="la-adj", pos="adj", tags=(), **extra):
    return {
        "pos": pos,
        "head_templates": [{"name": template, "expansion": expansion}],
        "senses": [{"glosses": ["x"], "tags": list(tags), **extra}],
    }


def adjective(head, *forms, tags=("declension-1", "declension-2"), **extra):
    return [form(f, t) for f, t in forms], page(head + " (...)", tags=tags, **extra)


def test_unlisted_comparison_and_adverb_are_generated():
    # serēnus lists an adverb but no comparison
    forms, entry = adjective("serēnus", ("serēna", "feminine"), ("serēnē", "adverb"))
    added = spellings(comparison(forms, {}, entry))
    assert {"serēnior", "serēniōrī", "serēnius", "serēnissima", "serēnissimē"} <= added
    assert "serēnē" not in added

    # officiōsus lists comparison but no adverb (its officiōse is a vocative)
    forms, entry = adjective(
        "officiōsus",
        ("officiōsior", "comparative"),
        ("officiōsissimus", "superlative"),
    )
    assert spellings(comparison(forms, {}, entry)) == {"officiōsē"}


def test_third_declension_and_irregular_superlatives():
    forms, entry = adjective(
        "pervicāx", ("pervicācis", "genitive"), tags=["declension-3"]
    )
    added = spellings(comparison(forms, {}, entry))
    assert {"pervicācius", "pervicācissimum", "pervicāciter"} <= added

    forms, entry = adjective(
        "prūdēns", ("prūdentis", "genitive"), tags=["declension-3"]
    )
    assert "prūdenter" in spellings(comparison(forms, {}, entry))

    forms, entry = adjective("facilis", ("facile", "neuter"), tags=["declension-3"])
    assert {"faciliōrī", "facillimus", "faciliter"} <= spellings(
        comparison(forms, {}, entry)
    )

    forms, entry = adjective("pulcher", ("pulchra", "feminine"))
    assert {"pulchrior", "pulcherrima", "pulchrē"} <= spellings(
        comparison(forms, {}, entry)
    )


def test_adjectives_that_do_not_compare_are_left_alone():
    for head in ("idōneus", "Rōmānus", "bellicus", "marīnus", "nātūrālis"):
        forms, entry = adjective(head)
        assert comparison(forms, {}, entry) == [], head
    forms, entry = adjective("optimus", tags=["superlative"])
    assert comparison(forms, {}, entry) == []

    # A participle only, and one used as an adjective
    amatus = page("amātus (...)", "la-part", "verb", form_of=[{"word": "amō"}])
    assert comparison([], {}, amatus) == []
    meritus = [form("meritō", "adverb")]
    meritus_page = page("meritus (...)", "la-part", "verb", form_of=[{"word": "mereō"}])
    assert "meritissimā" in spellings(comparison(meritus, {}, meritus_page))
    amandus = page("amandus (...)", "la-part", "verb")
    assert comparison([], {}, amandus) == []


def test_a_page_of_another_word_does_not_block_a_comparative():
    forms, entry = adjective("blandus", ("blanda", "feminine"))
    # blandior is a verb; blandissimus would be the superlative's own page
    known = {"blandior": {"verb"}, "blandissimus": {"adj"}}
    added = spellings(comparison(forms, known, entry))
    assert "blandior" in added
    assert "blandissimī" not in added


def test_syncopated_perfects():
    forms = [
        form("adventāvī", "active", "perfect"),
        form("adventāvisse", "active", "infinitive", "perfect"),
        form("adventāvērunt", "perfect", "plural"),
        form("adventāvēre", "perfect", "plural"),
        form("adventāverat", "pluperfect"),
    ]
    added = spellings(syncopated(forms))
    assert added == {"adventāsse", "adventārunt", "adventārat"}

    forms = [form("audīvī", "active", "perfect"), form("audīvit"), form("audīvisse")]
    assert spellings(syncopated(forms)) == {"audiī", "audiit", "audīsse"}


def test_an_alternative_spelling_is_inflected():
    forms = [form("Cēphīsus"), form("Cēphīsī"), form("Cēphīsum")]
    assert spellings(respelled(forms, "Cēphīsus", "Cēphissus")) == {
        "Cēphissus",
        "Cēphissī",
        "Cēphissum",
    }
    forms = [form("āvehō"), form("āvēxisse")]
    assert spellings(respelled(forms, "āvehō", "abvehō")) == {"abvehō", "abvēxisse"}
    # A difference in the ending is another word (catula, the feminine of catulus)
    assert respelled([form("catulus"), form("catulī")], "catulus", "catula") == []


def implied(word, pos, expansion, forms, **extra):
    entry = lemma(word, pos, expansion, ["x"], forms)
    entry.update(extra)
    return spellings(implied_forms(entry["forms"], {}, entry))


def test_prefixes_and_stems_are_respelled():
    adgemo = [("adgemō", ["canonical"]), ("adgemēns", ["participle", "present"])]
    assert {"aggemēns", "aggementis"} <= implied("adgemo", "verb", "adgemō", adgemo)

    # An assimilated prefix is respelled only when the etymology names it
    accipio = [("accipiō", ["canonical"])]
    assert "adcipiō" not in implied("accipio", "verb", "accipiō", accipio)
    assert "adcipiō" in implied(
        "accipio", "verb", "accipiō", accipio, etymology_text="From ad- + capiō."
    )

    refero = [("rettulī", ["active", "perfect"]), ("rettulērunt", ["perfect"])]
    assert {"retulī", "retulērunt"} <= implied("refero", "verb", "referō", refero)
    adul = [("adulēscentiae", ["genitive"])]
    assert "adolēscentiae" in implied("adulescentia", "noun", "adulēscentia", adul)


def test_greek_accusatives_names_and_feminines():
    acis = [("Ācin", ["accusative", "singular"])]
    assert "Ācim" in implied("Acis", "name", "Ācis m sg", acis)
    typhoeus = [("Typhōea", ["accusative", "singular"])]
    assert "Typhōeum" in implied("Typhoeus", "name", "Typhōeus m sg", typhoeus)

    iaspis = [
        ("iaspidem", ["accusative", "singular"]),
        ("iaspidēs", ["accusative", "plural"]),
    ]
    greek = {
        "senses": [{"glosses": ["jasper"], "tags": ["declension-3"]}],
        "etymology_templates": [{"name": "der", "args": {"1": "la", "2": "grc"}}],
    }
    assert {"iaspida", "iaspidas"} <= implied(
        "iaspis", "noun", "iaspis f", iaspis, **greek
    )
    assert "iaspida" not in implied("iaspis", "noun", "iaspis f", iaspis)

    assert {"Anaximandrī", "Anaximandrum"} <= implied(
        "Anaximander", "name", "Anaximander m", []
    )
    philoctetes = [("Philoctētae", ["genitive"])]
    assert "Philoctētem" in implied("Philoctetes", "name", "Philoctētēs m", philoctetes)
    lydus = [("Lȳdum", ["accusative", "singular"])]
    assert "Lȳdōrum" in implied("Lydus", "name", "Lȳdus m sg", lydus)

    catulus = [("catula", ["feminine"])]
    assert {"catulae", "catulam"} <= implied("catulus", "noun", "catulus m", catulus)


def test_genitive_plural_in_um():
    prudens = [("prūdentium", ["genitive", "plural"])]
    assert "prūdentum" in implied("prudens", "adj", "prūdēns", prudens)


def test_enclitics_are_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    que = lemma("-que", "conj", "-que", ["and"])
    ve_suffix = lemma("-ve", "suffix", "-ve", ["vocative of -vus"])
    ending = lemma("-ibus", "noun", "-ibus", ["dative plural of -ēs"])
    src = tmp_path / "kaikki-la.jsonl"
    src.write_text(
        "".join(json.dumps(e) + "\n" for e in (que, ve_suffix, ending)),
        encoding="utf-8",
    )
    with open(merge_dump(str(src), LATIN).path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]
    assert [e["word"] for e in entries] == ["-que"]
    # A tap on the que a book splits off (virum que) reaches it: the hyphen weighs nothing
    assert "-que" in Entry(find(entries, "-que", "conj"), LATIN).all_forms
