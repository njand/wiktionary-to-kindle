"""Forms added during sort_jsonl: generated declensions and alternative spellings."""

import json

from wiktionary_to_kindle.languages import LATIN
from wiktionary_to_kindle.languages.la_forms import decline
from wiktionary_to_kindle.merge.forms import GENERATED, enrich_forms
from wiktionary_to_kindle.merge.sort import merge_dump
from wiktionary_to_kindle.models.entry import Entry

from .test_sort_merge import find, forms_of, lemma, pointer


def form(word, *tags):
    return {"form": word, "tags": list(tags)}


def spellings(pairs):
    return {spelling for spelling, _tags in pairs}


def test_participles_without_a_page_are_declined():
    present = decline(form("dīcēns", "active", "participle", "present"), set())
    assert {"dīcentis", "dīcentem", "dīcentium", "dīcentibus"} <= spellings(present)
    parse = ["active", "participle", "present", "masculine", "feminine", "neuter"]
    assert ("dīcentis", [*parse, "genitive", "singular"]) in present

    perfect = decline(form("dictus", "participle", "passive", "perfect"), set())
    assert {"dictī", "dicta", "dictam", "dictōrum", "dictās"} <= spellings(perfect)
    gerundive = decline(form("dīcundus", "future", "participle", "passive"), set())
    assert "dīcundōrum" in spellings(gerundive)


def test_forms_with_a_page_are_not_declined():
    assert decline(form("amātus", "participle", "passive", "perfect"), {"amātus"}) == []
    # Declined cells and the participle "-" Kaikki gives deponents are not nominatives
    assert (
        decline(form("amātī", "participle", "perfect", "plural", "genitive"), set())
        == []
    )
    assert decline(form("-", "participle", "passive", "present"), set()) == []
    # Impersonal gerundive
    assert decline(form("pluendum", "future", "participle", "passive"), set()) == []


def test_comparative_superlative_and_adverb():
    forms = [
        form("altus", "canonical"),
        form("altior", "comparative"),
        form("altissimus", "superlative"),
        form("altē", "adverb"),
    ]
    added = {
        f["form"]: f["tags"] for f in enrich_forms(forms, set(), LATIN)[len(forms) :]
    }
    assert {"altius", "altiōris", "altiōrem", "altiōribus"} <= set(added)
    assert {"altissimī", "altissimae", "altissimōrum"} <= set(added)
    assert added["altissimē"] == ["adverb", "superlative", GENERATED]
    assert all(GENERATED in tags for tags in added.values())

    # The adverb's own page has its superlative; the comparative's page its declension
    added = enrich_forms(forms, {"altē", "altior"}, LATIN)[len(forms) :]
    assert "altissimē" not in {f["form"] for f in added}
    assert "altiōrem" not in {f["form"] for f in added}


def test_listed_forms_are_not_generated_again():
    forms = [form("celsior", "comparative"), form("celsiōrem", "accusative")]
    added = enrich_forms(forms, set(), LATIN)[len(forms) :]
    assert "celsiōrem" not in {f["form"] for f in added}


def test_alternative_spellings_without_a_page_are_kept():
    forms = [
        form("inlābor", "alternative"),
        form("abs", "alternative"),
        form("prelium", "Medieval-Latin", "alternative"),
        form("*luttra", "Latin", "alternative", "vulgar"),
        form("rendō", "Late-Latin", "alternative", "reconstruction"),
    ]
    merged = [form("caussa", "alternative")]  # merged from its own page: kept
    kept = enrich_forms(forms, {"abs", "caussa"}, LATIN, merged)
    assert [f["form"] for f in kept] == ["inlābor", "prelium", "caussa"]


def test_alternative_and_generated_forms_reach_the_entry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = [
        lemma(
            "dico",
            "verb",
            "dīcō (present infinitive dīcere); third conjugation",
            ["to say"],
            [
                ("dīcēns", ["active", "participle", "present"]),
                ("dictus", ["participle", "passive", "perfect"]),
                ("deicō", ["alternative"]),
            ],
        ),
        # dictus has a page of its own, so its declension is not generated
        pointer(
            "dictus",
            "verb",
            "dictus (feminine dicta, neuter dictum); participle",
            "said, uttered",
            "dīcō",
            forms=[("dictī", ["genitive", "singular"])],
        ),
    ]
    src = tmp_path / "kaikki-la.jsonl"
    src.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    merged = merge_dump(str(src), LATIN)
    with open(merged.path, encoding="utf-8") as f:
        sorted_entries = [json.loads(line) for line in f]

    dico = find(sorted_entries, "dico", "verb")
    assert "dīcentis" in forms_of(dico)
    assert "dictōrum" not in forms_of(dico)
    assert {"deicō", "dīcentis"} <= Entry(dico, LATIN).all_forms
