"""Corpus lookup coverage: how many words in real Latin texts open an entry, and why not.

Each token is resolved against the dictionary's own labels with the Kindle's matching rules
(see utils.kindle_fold and the kindling README):

  unique     every label it reaches belongs to one entry
  spelling   several entries, and an exact-spelling (or same-letters-ignoring-case) label
             picks the one the popup shows first, the way the device does
  ambiguous  several entries and no rule picks one: the index's stored order decides
             which the popup shows first
  miss       no label has the same weights, so nothing opens

The popup lists every entry a tap reaches, so "spelling" and "ambiguous" differ only in
which entry comes first.

Misses are retried with variants a reader's text often has but Wiktionary's headwords do not
(enclitics, u for consonantal v, j for consonantal i) to name the likely cause.
Optionally, the most frequent words are also checked with kindling's simulator, which models
the real index order, to confirm the static prediction.
"""

import os
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from .kindling import lookup

ENCLITICS = ("que", "ne", "ve")
ROMAN_NUMERAL = re.compile(r"[IVXLCDM]+")
CONSONANTAL_U = re.compile(r"[uU](?=[aeiouāēīōūAEIOU])")
OUTCOMES = ("unique", "spelling", "ambiguous", "miss")


def resolve(index, word):
    """Return (outcome, labels reached) for a tapped word."""
    run = index.run(word)
    if not run:
        return "miss", run
    if len({entry.key for _, entry in run}) == 1:
        return "unique", run
    for matches in (
        {entry.key for label, entry in run if label == word},
        {entry.key for label, entry in run if label.lower() == word.lower()},
    ):
        if len(matches) == 1:
            return "spelling", run
        if matches:
            break
    return "ambiguous", run


def miss_cause(index, word):
    for causes, candidate in _variants(word):
        if index.run(candidate):
            return " + ".join(causes)
    if ROMAN_NUMERAL.fullmatch(word):
        return "roman numeral"
    if word[:1].isupper():
        return "unknown (capitalized)"
    return "unknown"


def _variants(word):
    bases = [((), word)]
    for enclitic in ENCLITICS:
        if word.lower().endswith(enclitic) and len(word) > len(enclitic) + 1:
            bases.append(((f"enclitic -{enclitic}",), word[: -len(enclitic)]))

    for causes, base in bases:
        spellings = [(causes, base)]
        if "j" in base.lower():
            spellings.append(
                (causes + ("j for i",), base.replace("j", "i").replace("J", "I"))
            )
        if CONSONANTAL_U.search(base):
            spellings += [
                (
                    c + ("u for v",),
                    CONSONANTAL_U.sub(lambda m: "vV"[m.group().isupper()], w),
                )
                for c, w in list(spellings)
            ]
        for variant in spellings:
            if variant[0]:
                yield variant


def measure(index, counts, top=30):
    """Summarize one Counter of tokens."""
    tokens, types = Counter(), Counter()
    misses = defaultdict(Counter)
    ambiguous = Counter()
    heads = {}
    for word, n in counts.items():
        outcome, run = resolve(index, word)
        tokens[outcome] += n
        types[outcome] += 1
        if outcome == "miss":
            misses[miss_cause(index, word)][word] += n
        elif outcome == "ambiguous":
            ambiguous[word] += n
            heads[word] = list(dict.fromkeys(entry.headword for _, entry in run))[:6]

    total_tokens, total_types = sum(tokens.values()), sum(types.values())
    return {
        "tokens": total_tokens,
        "types": total_types,
        "token_share": {o: _share(tokens[o], total_tokens) for o in OUTCOMES},
        "type_share": {o: _share(types[o], total_types) for o in OUTCOMES},
        "miss_causes": {
            cause: {
                "tokens": sum(words.values()),
                "types": len(words),
                "top": words.most_common(top),
            }
            for cause, words in sorted(
                misses.items(), key=lambda kv: -sum(kv[1].values())
            )
        },
        "ambiguous_top": [[w, n, heads[w]] for w, n in ambiguous.most_common(top)],
    }


def verify_with_kindling(index, counts, kindling, mobi, limit, jobs=None):
    """Check the static prediction for the `limit` most frequent words against kindling."""
    words = [w for w, _ in counts.most_common(limit)]
    with ThreadPoolExecutor(max_workers=jobs or os.cpu_count()) as pool:
        results = dict(zip(words, pool.map(lambda w: lookup(kindling, mobi, w), words)))

    disagreements = []
    for word in words:
        predicted = resolve(index, word)[0] != "miss"
        if predicted != results[word]["opens"]:
            disagreements.append([word, predicted, results[word]["opens"]])
    return {
        "checked": len(words),
        "agree": len(words) - len(disagreements),
        "hidden_labels": sum(r["hidden"] for r in results.values()),
        "disagreements": disagreements,
    }


def opens(summary):
    """Share of tokens that open something."""
    share = summary["token_share"]
    return share["unique"] + share["spelling"] + share["ambiguous"]


def diff(old, new, threshold=0.005):
    """Return (markdown, regressions) comparing two coverage reports. A source regresses when
    the share of its tokens that open something falls by more than threshold (0.005 = half
    a percentage point). The share left to index order and kindling's hidden labels are
    shown but not judged: the popup lists every entry a tap reaches, so they only decide
    which comes first. A source in only one report is listed but not compared, and so is
    "all" when the sources differ."""
    lines = [
        "| Source | Opens before | Opens now | Change | Ambiguous before | Ambiguous now |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    regressions = []
    same_sources = set(old["sources"]) == set(new["sources"])
    for name in dict.fromkeys([*new["sources"], *old["sources"]]):
        before, after = old["sources"].get(name), new["sources"].get(name)
        if name == "all" and not same_sources:
            lines.append(f"| {name} | | | sources differ | | |")
            continue
        if not before or not after:
            lines.append(f"| {name} | | | {'new' if after else 'removed'} | | |")
            continue
        if before["tokens"] != after["tokens"]:  # the text itself changed
            name = f"{name} ({before['tokens']:,} → {after['tokens']:,} tokens)"
        change = opens(after) - opens(before)
        ambiguous = [s["token_share"]["ambiguous"] for s in (before, after)]
        lines.append(
            f"| {name} | {opens(before):.1%} | {opens(after):.1%} | {change * 100:+.1f} pp "
            f"| {ambiguous[0]:.1%} | {ambiguous[1]:.1%} |"
        )
        if change < -threshold:
            regressions.append(
                f"{name}: tokens that open something {change * 100:+.1f} pp"
            )

    if "kindling" in old and "kindling" in new:
        hidden = [r["kindling"]["hidden_labels"] for r in (old, new)]
        lines += [
            "",
            f"Words with labels the index order hides: {hidden[0]} → {hidden[1]}",
        ]
    return "\n".join(lines), regressions


def to_markdown(report):
    lines = [
        "| Source | Tokens | Opens | Picked by spelling | Ambiguous | Miss |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, summary in report["sources"].items():
        share = summary["token_share"]
        lines.append(
            f"| {name} | {summary['tokens']:,} | {opens(summary):.1%} | {share['spelling']:.1%} "
            f"| {share['ambiguous']:.1%} | {share['miss']:.1%} |"
        )

    overall = report["overall"]
    lines += ["", "**Misses by likely cause** (all sources, by token count)", ""]
    lines += [
        "| Cause | Tokens | Words | Most frequent |",
        "| --- | ---: | ---: | --- |",
    ]
    for cause, info in overall["miss_causes"].items():
        examples = ", ".join(f"{w} ({n})" for w, n in info["top"][:8])
        lines.append(
            f"| {cause} | {info['tokens']:,} | {info['types']:,} | {examples} |"
        )

    if overall["ambiguous_top"]:
        lines += [
            "",
            "**Most frequent ambiguous words** (index order picks the entry shown first)",
            "",
        ]
        lines += [
            f"- {w} ({n}): {', '.join(heads)}"
            for w, n, heads in overall["ambiguous_top"][:15]
        ]

    if "kindling" in report:
        k = report["kindling"]
        lines += [
            "",
            (
                f"**kindling check:** {k['agree']}/{k['checked']} most frequent words agree "
                f"with the static prediction; {k['hidden_labels']} have labels the index "
                "order hides."
            ),
        ]
        lines += [
            f"- {w}: predicted opens={p}, kindling opens={o}"
            for w, p, o in k["disagreements"][:20]
        ]
    return "\n".join(lines)


def _share(part, whole):
    return part / whole if whole else 0.0
