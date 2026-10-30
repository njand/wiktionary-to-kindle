"""Fetch, clean and tokenize the texts used to measure lookup coverage.

A manifest is a TSV of `name<TAB>format<TAB>url` lines (`#` comments). Formats:
  latinlibrary  an HTML page from thelatinlibrary.com (navigation and footer removed)
  latinlibrary-u  the same, with lowercase v written u, as editions such as the OCT print it
  macron-lines  plain text mixing Latin and English; keeps only lines with a macron
  tei           a TEI edition, such as Perseus's: the text of its edition, without notes
  tei:N         the same, only its top-level part numbered N (a book: tei:1)
  text          plain text, used as is
  conllu        a Universal Dependencies treebank: the text of each sentence (# text =)
  conllu:G      the same, only the sentences whose id starts with G_ (a genre: conllu:news)
  wikisource    a page rendered by Wikisource (action=render): its text, without the header,
                notes and references
"""

import html
import re
import urllib.request
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

HEADERS = {"User-Agent": "wiktionary-to-kindle coverage check"}
MACRONS = "āēīōūȳĀĒĪŌŪȲ"
# Letters plus combining marks, so a disputed vowel (ā̆) stays one token, and an apostrophe
# between letters, which a Kindle keeps in the word it looks up (Türkiye'nin)
LETTERS = r"(?:[^\W\d_]|[̀-ͯ])+"
TOKEN = re.compile(rf"{LETTERS}(?:['’]{LETTERS})*")


def read_manifest(path):
    sources = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, fmt, url = line.split("\t")
            sources.append((name, fmt, url))
    return sources


def load_source(name, fmt, url, cache_dir):
    """Return the cleaned text of a source, downloading it once into cache_dir."""
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"{name}.txt"
    if not cached.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        if url.startswith(("http://", "https://")):
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req) as response:
                raw = response.read().decode("utf-8", errors="replace")
        else:
            raw = Path(url).read_text(encoding="utf-8")
        tmp = cached.with_suffix(".part")
        tmp.write_text(clean(raw, fmt), encoding="utf-8")
        tmp.replace(cached)
    return cached.read_text(encoding="utf-8")


def clean(raw, fmt):
    if fmt == "latinlibrary-u":
        return clean(raw, "latinlibrary").replace("v", "u")
    if fmt == "latinlibrary":
        for pattern in (
            r"<head>.*?</head>",
            r"<div class=\"footer\">.*?</div>",
            r"<p class=\"internal_navigation\">.*?</p>",
        ):
            raw = re.sub(pattern, " ", raw, flags=re.DOTALL | re.IGNORECASE)
        return html.unescape(re.sub(r"<[^>]+>", " ", raw))
    if fmt == "macron-lines":
        return "\n".join(
            line for line in raw.splitlines() if any(c in line for c in MACRONS)
        )
    if fmt == "tei" or fmt.startswith("tei:"):
        return tei_text(raw, fmt.partition(":")[2] or None)
    if fmt == "text":
        return raw
    if fmt == "conllu" or fmt.startswith("conllu:"):
        return conllu_text(raw, fmt.partition(":")[2] or None)
    if fmt == "wikisource":
        return wikisource_text(raw)
    raise ValueError(f"unknown corpus format: {fmt}")


TEI = "{http://www.tei-c.org/ns/1.0}"
# Text in a TEI edition that is no part of the work: notes, references, editors' headings
TEI_SKIPPED = {f"{TEI}{tag}" for tag in ("note", "bibl", "head", "label", "ref")}


def tei_text(raw, part=None):
    """The words of a TEI edition (its div type="edition"), or of its top-level part
    numbered part, separated by single spaces. Every element starts a new word: Perseus
    puts milestones and verses between words, not inside them."""
    edition = next(
        div
        for div in ElementTree.fromstring(raw).iter(f"{TEI}div")
        if div.get("type") == "edition"
    )
    if part is not None:
        edition = next(
            div for div in edition.findall(f"{TEI}div") if div.get("n") == part
        )
    lines = []

    def walk(element):
        if element.tag in TEI_SKIPPED:
            return
        if element.text:
            lines.append(element.text)
        for child in element:
            walk(child)
            if child.tail:
                lines.append(child.tail)

    walk(edition)
    return " ".join(" ".join(lines).split())


def conllu_text(raw, genre=None):
    """The sentences of a CoNLL-U treebank, one per line, as their # text = lines print
    them, or only those whose sent_id starts with genre and an underscore."""
    lines, keep = [], genre is None
    for line in raw.splitlines():
        if line.startswith("# sent_id = "):
            keep = genre is None or line[len("# sent_id = ") :].startswith(genre + "_")
        elif line.startswith("# text = ") and keep:
            lines.append(line[len("# text = ") :])
    return "\n".join(lines)


# A Wikisource page's text is in paragraphs and, for dialogue, <dd> lines; the header, the
# box linking the Ottoman Turkish original and the notes are in other elements
WIKISOURCE_TEXT = re.compile(r"<(p|dd)\b[^>]*>(.*?)</\1>", re.DOTALL)


def wikisource_text(raw):
    """The paragraphs and dialogue lines of a page Wikisource rendered, without
    footnote markers, one per line."""
    raw = re.sub(r"<sup\b.*?</sup>", "", raw, flags=re.DOTALL)
    return "\n".join(
        html.unescape(re.sub(r"<[^>]+>", "", text))
        for _, text in WIKISOURCE_TEXT.findall(raw)
    )


def tokenize(text):
    """The words of text as it prints them: not normalized, since a Kindle weighs a
    decomposed accent or a Greek oxia as written (utils.kindle_fold)."""
    return Counter(TOKEN.findall(text))
