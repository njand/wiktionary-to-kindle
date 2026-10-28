"""Fetch, clean and tokenize the Latin texts used to measure lookup coverage.

A manifest is a TSV of `name<TAB>format<TAB>url` lines (`#` comments). Formats:
  latinlibrary  an HTML page from thelatinlibrary.com (navigation and footer removed)
  latinlibrary-u  the same, with lowercase v written u, as editions such as the OCT print it
  macron-lines  plain text mixing Latin and English; keeps only lines with a macron
  text          plain text, used as is
"""

import html
import re
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

HEADERS = {"User-Agent": "wiktionary-to-kindle coverage check"}
MACRONS = "āēīōūȳĀĒĪŌŪȲ"
# Letters plus combining marks, so a disputed vowel (ā̆) stays one token
TOKEN = re.compile(r"(?:[^\W\d_]|[̀-ͯ])+")


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
    if fmt == "text":
        return raw
    raise ValueError(f"unknown corpus format: {fmt}")


def tokenize(text):
    return Counter(TOKEN.findall(unicodedata.normalize("NFC", text)))
