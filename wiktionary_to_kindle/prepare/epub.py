"""Rewrite the text of an EPUB with words split by prepare.segment, leaving everything else
as it was: markup, images, styles, and the archive's layout (mimetype first, stored).

Each block of a chapter (a paragraph, heading, list item, ...) is read as text for the
sentences the segmenter decides on; the splits are then written into the block's text
between tags, so a word split across inline markup (rare) is left whole. A split word is
wrapped in a span that keeps it on one line, since a line may break at a hair space.
"""

import html
import posixpath
import re
import zipfile
from xml.etree import ElementTree

from ..quality.corpus import TOKEN
from .segment import HAIR, segment_text

NOWRAP = '<span style="white-space: nowrap">{}</span>'
BLOCK = re.compile(
    r"(<(?:p|div|h[1-6]|li|blockquote|td|th|dd|dt|figcaption|pre)\b[^>]*>)",
    re.IGNORECASE,
)
CONTAINER = "META-INF/container.xml"
OPF_NS = "{http://www.idpf.org/2007/opf}"
XHTML_TYPES = {"application/xhtml+xml", "text/html"}


def chapters(archive):
    """The archive names of the book's XHTML documents, from its OPF manifest."""
    container = ElementTree.fromstring(archive.read(CONTAINER))
    rootfile = next(e for e in container.iter() if e.tag.endswith("rootfile"))
    opf_path = rootfile.get("full-path")
    opf = ElementTree.fromstring(archive.read(opf_path))
    base = posixpath.dirname(opf_path)
    return [
        posixpath.normpath(posixpath.join(base, item.get("href")))
        for item in opf.iter(f"{OPF_NS}item")
        if item.get("media-type") in XHTML_TYPES
    ]


def prepare_epub(src, dst, lexicon, decide, nowrap=True):
    """Write dst, a copy of the EPUB src with its words split; return the split report
    [(word, sentence, Split or None)]."""
    report = []
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        texts = set(chapters(zin))
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename in texts:
                text = data.decode("utf-8")
                data = prepare_xhtml(text, lexicon, decide, report, nowrap).encode(
                    "utf-8"
                )
            compress = (
                zipfile.ZIP_STORED
                if info.filename == "mimetype"
                else zipfile.ZIP_DEFLATED
            )
            zout.writestr(info, data, compress_type=compress)
    return report


def prepare_xhtml(text, lexicon, decide, report, nowrap=True):
    """text, an XHTML document, with its body's words split."""
    match = re.search(r"<body\b[^>]*>", text, re.IGNORECASE)
    if not match:
        return text
    head, body = text[: match.end()], text[match.end() :]
    pieces = BLOCK.split(body)
    return head + "".join(
        _prepare_block(piece, lexicon, decide, report, nowrap) if i % 2 == 0 else piece
        for i, piece in enumerate(pieces)
    )


def _prepare_block(block, lexicon, decide, report, nowrap):
    """A block's markup with the words the segmenter splits rewritten in its text."""
    plain = html.unescape(re.sub(r"<[^>]+>", "", block))
    if not plain.strip():
        return block
    _, decisions = segment_text(plain, lexicon, decide)
    report += decisions
    splits = {}
    for word, _sentence, split in decisions:
        if split:
            splits.setdefault(word, split.spelling)
    if not splits:
        return block

    def rewrite_text(m):
        # Words are matched in the text as it reads (an apostrophe may be &#8217;); a
        # run with no split is left exactly as it was, entities included
        text = html.unescape(m.group())
        pieces, last = [], 0
        for word in TOKEN.finditer(text):
            spelling = splits.get(word.group())
            if spelling:
                pieces.append(html.escape(text[last : word.start()], quote=False))
                pieces.append(NOWRAP.format(spelling) if nowrap else spelling)
                last = word.end()
        if not pieces:
            return m.group()
        return "".join(pieces) + html.escape(text[last:], quote=False)

    # Only text between tags; the tags themselves are left alone
    return re.sub(r"(?<=>)[^<]+|^[^<]+", rewrite_text, block)


def prepare_plain(text, lexicon, decide):
    """Plain text with its words split (no markup): for measuring and for .txt books."""
    out, report = [], []
    for paragraph in text.split("\n"):
        prepared, decisions = segment_text(paragraph, lexicon, decide)
        out.append(prepared)
        report += decisions
    return "\n".join(out), report


__all__ = ["HAIR", "prepare_epub", "prepare_plain", "prepare_xhtml"]
