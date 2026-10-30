# Turkish: decisions made without asking

While carrying out ROADMAP Stages 14–19 (2026-10-29), the user asked for the Turkish dictionary to be taken to a release without stopping for questions, with each judgement call logged here to review afterwards. Each entry says what was decided, why, and what would change it.

## Stage 14: device check

1. **The device check is not done; the plan goes ahead on assumptions.** No Kindle is reachable from this machine. The test book is built (`outputs/device-test-tr/`). Assumed until it is checked:
   - A long press stops at a hair space inside a word, as it did between a Latin word and its enclitic (2026-10-29). Everything below depends on this; it is the first thing to check.
   - A line may break at a hair space, so `prepare-book` wraps each split word in `<span style="white-space: nowrap">`. If the device shows no breaks without it, the span is harmless; if `nowrap` is ignored, a split word may wrap, which is ugly but still looks up.
   - The selection takes in an apostrophe (kindling's word formatting implies it). So a name whose suffixed form opens nothing or the wrong word (`Ali'nin` reaches `alının`) gets a hair space after the apostrophe: `Ali'` then `nin`. If the device stops at the apostrophe anyway, the extra space changes nothing.
   - The gap a hair space leaves is acceptable. If it is too visible, nothing in the plan replaces it: no other separator splits the selection.

## Model access

2. **No model can be called from this machine.** There is no `ANTHROPIC_API_KEY`, and the Claude Code binary bundled with the desktop app is not logged in for headless use (`claude -p` answers "Not logged in"). So the segmenter talks to the Anthropic API (key from the environment) or to a logged-in `claude` CLI, caches every decision, and falls back to the rooted heuristic (decision 9) when neither is available. The evaluation decisions were made by Claude through Claude Code subagents reading the same prompt, and written into the same cache format.

## Stage 15: the dictionary for split words

3. **One suffix-chain entry per spelling, labelled with a leading hyphen** (`-lerimizden`). The hyphen weighs nothing, so a tap on `lerimizden` reaches it, but kindling stores a plain label first, so a word spelled like a chain (`de`, `in`, `dan`) is listed before the suffix entry. An entry lists every analysis of its spelling (`-leri`: their / plural + acc. / plural + his/her).
4. **What the suffix grammar covers** (`languages/tr_suffixes.py`): nouns, with plural, possessive, case, `-ki` (with a plural and case after it) and the copula with its persons; verbs, with the passive, negation, ability, the tenses with persons and a copula, imperatives, verbal nouns and participles with possessive and case (no copula after them), infinitives and converbs; and six derivational suffixes (`-lI`, `-sIz`, `-lIk`, `-CI`, `-CA`, `-CIk`) with a short tail. Left out: causatives and reciprocals (Wiktionary has those verbs as words), and the copula after verbal nouns and participles. That last cut took the spellings from 447,000 to 58,000; with the passive and derivations added back the grammar makes 114,013 spellings.
5. **Stem variants are read from each entry's own forms**, not guessed: a noun's stem from its accusative (`kitabı` → `kitab`), a verb's from its progressive (`gidiyor` → `gid`, `bekliyor` → `bekli`). Names are left out (`NATO'yu` would give `NATO'y`).
6. **Descendants are kept in every language** for Turkish (Latin keeps five, Greek three). They close the entry, so they cost nothing on the popup's first screen.

## Stage 16: prepare-book

7. **Which words are split**: a word that opens nothing whole, or a name whose part before the apostrophe opens something the whole word does not (`Ali'nin` reaches `alının`). A word that opens whole is left alone even when it is a homograph a suffix made (`vardı`): splitting it (`var` + `dı`) reaches the same entries, since `var` is also varmak's imperative.
8. **Split words are wrapped in `white-space: nowrap`** by default (`--no-nowrap` to turn it off), until the device check says whether a line breaks at a hair space.
9. **Without a model, `prepare-book` uses `rooted`**, not greedy: the shortest stem of the lemma the longest stem belongs to, so a chain stays together (`ol` + `madığını`, not `olmadığın` + `ı`). Cached model decisions are used either way.

## Stage 17: the segmenter

10. **Model: `claude-opus-5-5`** (the default the Anthropic API guidance gives), through the official `anthropic` package (an optional dependency, `pip install "wiktionary-to-kindle[segment]"`), with structured JSON output, and with server-side refusal fallbacks turned on (`fallbacks: "default"`), so a declined request is retried on another model. A request that is still refused leaves its words whole. `--model` and `--backend claude-cli` choose otherwise.
11. **Effort `low`.** Each request is a choice among a few given options, and thinking output is most of the cost (see below). `--effort medium` or higher if the quality check says it helps; the evaluation below was not run per effort level.
12. **Evaluation by subagents.** No model could be called from a script here (decision 2), so Claude subagents answered the exported requests for BOUN's held-out test part (460 requests, 732 words) under the same system prompt, and the answers were imported into the cache (`outputs/measure/tr-stage17/`). Scored against BOUN's gold lemmas, a decision being right when it splits after a stem of the gold lemma, or leaves the word whole when no option has it: greedy 77.6%, rooted 78.1%, the model 78.7%. The model leaves 47 words whole (names, look-alike stems such as `Şener`, `Boca`, `bardacıkları`) and makes 113 misleading splits where greedy and rooted make 134. The gain is smaller than hoped: the candidates (a stem that opens, a chain the grammar accepts) already exclude most wrong splits, and BOUN lemmatizes derived words to their roots (`kullanılması` → kullan), so it marks some good derived stems wrong.
13. **Cost estimate** (not measured against the API): an 80,000-word novel has about 6,000 words to decide in about 4,000 sentences, so about 1 million uncached input tokens ($4 at Opus 5.5 prices), the system prompt cached, and 0.2–1.5 million output tokens depending on how much the model thinks ($4–30). Roughly $10 a novel at effort `low`; Claude Sonnet 5.5 (`--model claude-sonnet-5-5`) would halve it. Run it once per book: the cache makes reruns free.
14. **Book text goes to the Anthropic API** when a model is used. That is the user's own book, sent under their own API account; `--decide rooted` sends nothing.

## Stage 18: entries

15. **Principal parts on the head line**: a noun's definite accusative (`ev, evi`) and a verb's aorist (`gitmek, gider`), since they show the stem the suffixes go on (`kitab-ı`, `gid-er`). Wiktionary gives no other principal parts for Turkish.
16. **The popup order is left to the existing estimate** (how much Wiktionary says about an entry), so where a stem folds onto another word the larger entry comes first (`ol`: ölmek, then olmak). A frequency list would fix it; none with a clear licence was at hand, and the user asked to be consulted on corpus licences.

## Stage 19: release

17. **The release is the local build**, not pushed: GitHub Actions has no minutes left, and pushing or opening a pull request waits for the user. The workflow's Turkish step was not run on GitHub; its command was run locally.
18. **Turkish ships as "in testing"** in the pre-releases, like Ancient Greek, until the device check; the README says so.
19. **Latin is unchanged.** A Latin build on this branch writes pages byte-identical to one from `origin/main`, and a `.mobi` of the same size. Found on the way: the popup order sizes entries by their JSON as `jsonl.json_dumps` writes it, which differs with and without `orjson`, so a build without the `fast` extra ranks some homographs' soft hyphens differently (brūchus and brūcus swap). CI installs every extra, so releases are consistent; not changed here.
