"""Measure how a Turkish text reads after prepare-book.

For each source of a corpus manifest: the share of word tokens that open something whole,
and after preparation (whole, or split with a stem that opens); and, for a CoNLL-U source
such as BOUN, the share whose lemma the opened entry belongs to. Each word counts once,
however it is split.

Usage:
    python scripts/measure_prepared.py outputs/KindleDictionary-tr corpus/tr.tsv \
        --decide rooted [--decide greedy] [--cache decisions.jsonl] [--gold boun.conllu]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from wiktionary_to_kindle.prepare import model
from wiktionary_to_kindle.prepare.lexicon import Lexicon
from wiktionary_to_kindle.prepare.segment import (
    greedy,
    rooted,
    segment_text,
    words,
)
from wiktionary_to_kindle.quality.corpus import TOKEN, load_source, read_manifest
from wiktionary_to_kindle.utils import kindle_fold


def decider(name, cache):
    if name == "greedy":
        return greedy
    if name == "rooted":
        return rooted
    if name == "cache":
        return model.CachedDecider(cache, fallback=rooted)
    raise SystemExit(f"unknown decider {name}")


def measure_text(text, lexicon, decide):
    prepared, report = segment_text(text, lexicon, decide)
    counts = Counter()
    for word in TOKEN.finditer(text):
        counts["words"] += 1
        counts["whole"] += bool(words(lexicon, word.group()))
    counts["split"] = sum(1 for _, _, split in report if split)
    counts["opens"] = counts["whole"] + sum(
        1 for word, _, split in report if split and not words(lexicon, word)
    )
    return prepared, report, counts


def gold_tokens(conllu):
    """(sentence, [(form, lemma, upos)]) per sentence of a CoNLL-U file, with each
    multiword token as its surface form and the lemma of its first part."""
    sentence, tokens, until = None, [], 0
    for line in Path(conllu).read_text(encoding="utf-8").splitlines():
        if line.startswith("# text = "):
            sentence = line[len("# text = ") :]
        elif not line.strip():
            if sentence is not None:
                yield sentence, tokens
            sentence, tokens, until = None, [], 0
        elif not line.startswith("#"):
            cols = line.split("\t")
            if "-" in cols[0]:
                until = int(cols[0].split("-")[1])
                tokens.append([cols[1], None, None])
            elif "." not in cols[0]:
                if int(cols[0]) <= until:
                    if tokens[-1][1] is None:
                        tokens[-1][1:] = cols[2], cols[3]
                else:
                    tokens.append([cols[1], cols[2], cols[3]])
    if sentence is not None:
        yield sentence, tokens


def lemma_keys(lemma, upos):
    keys = {kindle_fold(lemma)}
    if upos in ("VERB", "AUX"):
        keys |= {kindle_fold(lemma + "mek"), kindle_fold(lemma + "mak")}
    return keys


def measure_gold(conllu, lexicon, decide, limit=None):
    """Of the word tokens that are not names, numbers or punctuation: the share that
    reach their lemma whole, and after preparation."""
    counts = Counter()
    for n, (sentence, tokens) in enumerate(gold_tokens(conllu)):
        if limit and n >= limit:
            break
        _, report = segment_text(sentence, lexicon, decide)
        chosen = {word: split for word, _, split in report}
        for form, lemma, upos in tokens:
            if upos in ("PUNCT", "NUM", "PROPN") or not TOKEN.fullmatch(form):
                continue
            keys = lemma_keys(lemma, upos)
            counts["tokens"] += 1
            whole = {kindle_fold(s.headword) for s in words(lexicon, form)}
            counts["right whole"] += bool(whole & keys)
            split = chosen.get(form)
            if split:
                counts["split"] += 1
                right = {kindle_fold(s.headword) for s in split.senses} & keys
                counts["right split"] += bool(right)
                counts["right after"] += bool(right)
            else:
                counts["right after"] += bool(whole & keys)
            counts["opens after"] += bool(whole or split)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dict_dir", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--decide", action="append", default=[])
    parser.add_argument("--cache", type=Path, help="model decisions (prepare.model)")
    parser.add_argument("--gold", type=Path, help="a CoNLL-U file with lemmas")
    parser.add_argument("--gold-limit", type=int)
    parser.add_argument("--cache-dir", type=Path, default=Path("corpus/cache"))
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    lexicon = Lexicon.load(args.dict_dir)
    results = {}
    for name in args.decide or ["rooted"]:
        decide = decider(name, args.cache)
        total = Counter()
        rows = {}
        for source, fmt, url in read_manifest(args.manifest):
            text = load_source(source, fmt, url, args.cache_dir)
            _, _, counts = measure_text(text, lexicon, decide)
            rows[source] = dict(counts)
            total += counts
        rows["all"] = dict(total)
        if args.gold:
            rows["gold"] = dict(
                measure_gold(args.gold, lexicon, decide, args.gold_limit)
            )
        results[name] = rows
        print(f"## {name}")
        print("| Source | Words | Opens whole | Split | Opens prepared |")
        print("| --- | ---: | ---: | ---: | ---: |")
        for source, c in rows.items():
            if source == "gold":
                continue
            w = c["words"]
            print(
                f"| {source} | {w:,} | {c['whole'] / w:.1%} | {c.get('split', 0) / w:.1%} "
                f"| {c['opens'] / w:.1%} |"
            )
        if args.gold:
            g = rows["gold"]
            t = g["tokens"]
            print(
                f"\nGold lemmas ({t:,} tokens): right whole {g['right whole'] / t:.1%}, "
                f"after preparation {g['right after'] / t:.1%}, opens {g['opens after'] / t:.1%}; "
                f"of {g['split']:,} split, {g['right split'] / max(g['split'], 1):.1%} "
                "split after a stem of the right lemma"
            )
    if args.output:
        args.output.write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
