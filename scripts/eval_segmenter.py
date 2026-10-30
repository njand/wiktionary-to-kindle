"""Score segmenter decisions against a treebank's gold lemmas (roadmap, Stage 17).

A decision on a word that needs one is right when it splits after a stem whose entries
include the word's gold lemma, or leaves the word whole when no candidate stem has that
lemma (so the reader is not sent to an unrelated word). Prints the share right for the
greedy and rooted baselines and for cached model decisions.

Usage:
    python scripts/eval_segmenter.py outputs/KindleDictionary-tr boun-test.conllu \
        --cache outputs/measure/tr-stage17/decisions.jsonl
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from measure_prepared import gold_tokens, lemma_keys

from wiktionary_to_kindle.prepare import model
from wiktionary_to_kindle.prepare.lexicon import Lexicon
from wiktionary_to_kindle.prepare.segment import greedy, rooted, sentences, target
from wiktionary_to_kindle.utils import kindle_fold


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dict_dir", type=Path)
    parser.add_argument("conllu", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    lexicon = Lexicon.load(args.dict_dir)
    cache = model.Cache(args.cache)
    scores = {name: Counter() for name in ("greedy", "rooted", "model")}
    for sentence, tokens in gold_tokens(args.conllu):
        for part in sentences(sentence):
            for form, lemma, upos in tokens:
                if form not in part or upos in ("PUNCT", "NUM"):
                    continue
                tgt = target(lexicon, form)
                record = tgt and cache.get(tgt, part)
                if not record:
                    continue
                keys = lemma_keys(lemma, upos)
                right = [
                    bool({kindle_fold(s.headword) for s in split.senses} & keys)
                    for split in tgt.splits
                ]
                choices = {
                    "greedy": greedy([tgt], part)[0],
                    "rooted": rooted([tgt], part)[0],
                    "model": record["choice"] - 1 if record["choice"] else None,
                }
                for name, choice in choices.items():
                    score = scores[name]
                    score["words"] += 1
                    if choice is None:
                        score["whole"] += 1
                        score["right"] += not any(right)
                    else:
                        score["split"] += 1
                        score["right"] += right[choice]
                        score["misleading"] += not right[choice] and not any(right)
    print("| Decider | Words | Right | Split | Left whole | Misleading splits |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for name, s in scores.items():
        n = s["words"]
        print(
            f"| {name} | {n} | {s['right'] / n:.1%} | {s['split']} | {s['whole']} | "
            f"{s['misleading']} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
