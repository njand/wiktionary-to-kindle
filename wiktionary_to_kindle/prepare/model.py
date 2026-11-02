"""The context-aware segmenter: a model reads each sentence and chooses, for every word that
needs it, among the candidate splits.

The model only chooses: the candidates come from the dictionary and the suffix grammar
(prepare.segment), so whatever it answers, a split it makes opens an entry. An answer that
names no candidate leaves the word whole.

Decisions are kept in a JSONL cache, one line per (word, sentence, candidates), so a book
prepared twice costs nothing the second time and comes out the same. The cache records
the model and date of each decision. Backends (--backend):
  anthropic   the Anthropic API through the `anthropic` package (pip install
              "wiktionary-to-kindle[segment]"), with the credentials the SDK finds
              (ANTHROPIC_API_KEY, or a profile from `ant auth login`)
  claude-cli  a logged-in Claude Code CLI (`claude -p`)

Without a backend, `--decide export` writes the requests to a file to be answered
elsewhere (export_requests); import_answers adds those answers to the cache.
"""

import datetime
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

PROMPT_VERSION = 1
DEFAULT_MODEL = "claude-opus-5-5"

SYSTEM = """You prepare Turkish e-books for readers who look words up in a Kindle \
dictionary. The Kindle looks up only the whole word a reader selects, with no stemming, \
so a word the dictionary does not list is split with a hair space between its stem and \
its suffixes; the reader then selects the stem, which opens its entry, or the suffixes, \
which open an entry that analyzes them.

For each numbered word you get the sentence it is in, what the word opens whole, and \
numbered options. Option 0 leaves the word whole. Every other option is a split: the \
stem, the entries the stem opens, and what the suffixes after it are.

Choose the option a careful Turkish teacher would choose for this sentence:
- The stem should open the dictionary word the writer meant here, with that meaning \
(yüzü: face or hundred, by the sentence).
- Prefer the stem of the word itself, so its suffixes stay together (ol + madığını, not \
olmadığın + ı; ev + lerimizden, not evler + imizden).
- But keep a derived word as the stem when the dictionary has it with the meaning in \
context (gözlükçü + ler, not gözlük + çüler; bulut + suz is right only if bulutsuz is \
not offered).
- Choose 0 when no split fits the meaning: a name or foreign word the stems only \
resemble (Boris + in is not bor + isin), or a stem that would open an unrelated word.

Also give the dictionary form (lemma) you take the word to be, in Turkish."""

SCHEMA = {
    "type": "object",
    "properties": {
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "choice": {"type": "integer"},
                    "lemma": {"type": "string"},
                },
                "required": ["number", "choice", "lemma"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["words"],
    "additionalProperties": False,
}


def key(target, sentence):
    """What a decision is cached by: the prompt version, the sentence, the word and its
    candidates (a new dictionary with other candidates asks again)."""
    options = "|".join(split.spelling for split in target.splits)
    raw = f"{PROMPT_VERSION}\t{sentence}\t{target.word}\t{options}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def prompt(targets, sentence):
    """The user message for one sentence and its targets."""
    lines = [f"Sentence: {sentence}", ""]
    for number, tgt in enumerate(targets, 1):
        whole = "; ".join(s.describe() for s in tgt.whole[:4]) or "nothing"
        lines.append(f"{number}. «{tgt.word}» (whole, it opens: {whole})")
        lines.append("   0: leave whole")
        for option, split in enumerate(tgt.splits, 1):
            senses = "; ".join(s.describe() for s in split.senses[:4])
            analyses = " / ".join(split.analyses[:3])
            lines.append(
                f"   {option}: {split.stem} + {split.rest} — stem opens: {senses}"
                f" — suffixes: {analyses}"
            )
        lines.append("")
    lines.append(
        'Answer with {"words": [{"number": 1, "choice": 0, "lemma": "..."}, ...]}, one '
        "item per numbered word."
    )
    return "\n".join(lines)


class Cache:
    def __init__(self, path):
        self.path = Path(path) if path else None
        self.decisions = {}
        if self.path and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    self.decisions[record["key"]] = record

    def get(self, target, sentence):
        return self.decisions.get(key(target, sentence))

    def add(self, target, sentence, choice, lemma, model):
        record = {
            "key": key(target, sentence),
            "word": target.word,
            "sentence": sentence,
            "choice": choice,
            "split": target.splits[choice - 1].spelling if choice else None,
            "lemma": lemma,
            "model": model,
            "date": datetime.date.today().isoformat(),
        }
        self.decisions[record["key"]] = record
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _index(record, target):
    """A cached choice as an index into target.splits, or None to leave it whole."""
    choice = record.get("choice") or 0
    return choice - 1 if 0 < choice <= len(target.splits) else None


class CachedDecider:
    """Decisions from the cache only; a word with none goes to fallback (a decider such
    as segment.rooted), or is left whole when there is no fallback."""

    def __init__(self, cache, fallback=None):
        self.cache = cache if isinstance(cache, Cache) else Cache(cache)
        self.fallback = fallback
        self.misses = 0

    def __call__(self, targets, sentence):
        choices = [None] * len(targets)
        missing = []
        for i, tgt in enumerate(targets):
            record = self.cache.get(tgt, sentence)
            if record:
                choices[i] = _index(record, tgt)
            else:
                missing.append(i)
        self.misses += len(missing)
        if missing and self.fallback:
            fallback = self.fallback([targets[i] for i in missing], sentence)
            for i, choice in zip(missing, fallback):
                choices[i] = choice
        return choices


class ModelDecider(CachedDecider):
    """Asks a model for every target the cache has no decision for, one request per
    sentence, and caches the answers."""

    def __init__(self, cache, backend="anthropic", model=DEFAULT_MODEL, effort="low"):
        super().__init__(cache)
        self.backend, self.model, self.effort = backend, model, effort
        self.requests = 0
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self._client = None

    def __call__(self, targets, sentence):
        missing = [t for t in targets if not self.cache.get(t, sentence)]
        if missing:
            answers = self.ask(missing, sentence)
            for number, tgt in enumerate(missing, 1):
                choice, lemma = answers.get(number, (0, ""))
                if not 0 <= choice <= len(tgt.splits):
                    choice = 0
                self.cache.add(tgt, sentence, choice, lemma, self.model)
        return super().__call__(targets, sentence)

    def ask(self, targets, sentence):
        """{number: (choice, lemma)} from one request."""
        text = prompt(targets, sentence)
        self.requests += 1
        if self.backend == "claude-cli":
            raw = self._ask_cli(text)
        else:
            raw = self._ask_api(text)
        return parse_answer(raw)

    def _ask_api(self, text):
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic()
        response = self._client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=[
                {"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}
            ],
            output_config={
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
            messages=[{"role": "user", "content": text}],
        )
        self.usage["input_tokens"] += response.usage.input_tokens or 0
        self.usage["output_tokens"] += response.usage.output_tokens or 0
        if response.stop_reason == "refusal":
            return "{}"  # every word of the sentence stays whole
        return next((b.text for b in response.content if b.type == "text"), "{}")

    def _ask_cli(self, text):
        binary = shutil.which("claude")
        if not binary:
            raise RuntimeError("the claude CLI is not on PATH")
        result = subprocess.run(
            [binary, "-p", "--output-format", "json", "--model", self.model],
            input=SYSTEM + "\n\n" + text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        reply = json.loads(result.stdout)
        if reply.get("is_error"):
            raise RuntimeError(f"claude CLI: {reply.get('result')}")
        return reply.get("result", "{}")


def parse_answer(raw):
    """{number: (choice, lemma)} from a model's JSON answer, ignoring anything else
    around the JSON object."""
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start : end + 1]) if start != -1 else {}
    except json.JSONDecodeError:
        return {}
    answers = {}
    for item in data.get("words", []):
        try:
            answers[int(item["number"])] = (
                int(item["choice"]),
                str(item.get("lemma", "")),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return answers


class Recorder:
    """A decider that answers nothing (the fallback decides) but records every request a
    model would get, for answering elsewhere (export_requests)."""

    def __init__(self, cache, fallback):
        self.cache = cache if isinstance(cache, Cache) else Cache(cache)
        self.fallback = fallback
        self.requests = {}

    def __call__(self, targets, sentence):
        missing = [t for t in targets if not self.cache.get(t, sentence)]
        if missing:
            request_id = hashlib.sha1(
                "".join(key(t, sentence) for t in missing).encode()
            ).hexdigest()[:12]
            self.requests[request_id] = {
                "id": request_id,
                "sentence": sentence,
                "keys": [key(t, sentence) for t in missing],
                "words": [t.word for t in missing],
                "splits": [[s.spelling for s in t.splits] for t in missing],
                "prompt": prompt(missing, sentence),
            }
        return CachedDecider(self.cache, self.fallback)(targets, sentence)


def export_requests(recorder, path):
    """Write the recorded requests as JSONL: id, prompt, and what an answer is matched
    by."""
    with Path(path).open("w", encoding="utf-8") as f:
        f.writelines(
            json.dumps(request, ensure_ascii=False) + "\n"
            for request in recorder.requests.values()
        )


def import_answers(requests_path, answers_path, cache, model):
    """Add answers ({"id": ..., "words": [{"number", "choice", "lemma"}]} per line) to
    the cache, matched to their requests. Returns how many decisions were added."""
    cache = cache if isinstance(cache, Cache) else Cache(cache)
    requests = {}
    for line in Path(requests_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            request = json.loads(line)
            requests[request["id"]] = request
    added = 0
    for line in Path(answers_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        answer = json.loads(line)
        request = requests.get(answer.get("id"))
        if not request:
            continue
        parsed = parse_answer(json.dumps(answer))
        for number, (record_key, word, splits) in enumerate(
            zip(request["keys"], request["words"], request["splits"]), 1
        ):
            choice, lemma = parsed.get(number, (0, ""))
            if not 0 <= choice <= len(splits):
                choice = 0
            record = {
                "key": record_key,
                "word": word,
                "sentence": request["sentence"],
                "choice": choice,
                "split": splits[choice - 1] if choice else None,
                "lemma": lemma,
                "model": model,
                "date": datetime.date.today().isoformat(),
            }
            cache.decisions[record_key] = record
            if cache.path:
                with cache.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            added += 1
    return added
