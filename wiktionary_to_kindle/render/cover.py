"""Draw book covers: each dictionary's own, and a plain one for test books.

A dictionary's title is set in DejaVu Serif, shipped in templates/ (the old Latin
cover's face); a test book's in the sans serif Pillow ships (Aileron). Neither depends on
the machine's fonts, so a cover comes out the same everywhere with the same Pillow."""

import io

from PIL import Image, ImageDraw, ImageFont

from ..utils import TEMPLATES

WIDTH, HEIGHT = 800, 1280  # the Kindle's 1:1.6
MARGIN = 60
RED = (139, 0, 0)  # the W of Wiktionary's logo
GREY = (80, 80, 80)


def dictionary_cover(name):
    """PNG bytes of the cover of the name-English dictionary: Wiktionary's letters, then
    "name-English" and "Wiktionary".

    A title too long for one line at nearly full size takes two ("Ancient Greek-" /
    "English"). Everything is then centred as one block, so the height a title saves or
    takes is shared above and below it."""
    cover = Image.new("RGB", (WIDTH, HEIGHT), "white")
    art = Image.open(TEMPLATES.joinpath("cover-art.png").open("rb")).convert("RGB")
    draw = ImageDraw.Draw(cover)
    title = title_lines(draw, name, 100)
    wiktionary = fit(draw, "Wiktionary", 130, serif)
    # Art to title, between title lines, title to Wiktionary
    gaps = [90] + [35] * (len(title) - 1) + [50]
    height = art.height + sum(gaps) + sum(map(ink_height, title + [wiktionary]))
    # Optical centre: a little more space below the block than above it
    y = (HEIGHT - height) * 4 // 9
    cover.paste(art, ((WIDTH - art.width) // 2, y))
    y += art.height
    for line, gap in zip(title, gaps):
        y = place(draw, line, y + gap, RED)
    place(draw, wiktionary, y + gaps[-1], GREY)
    return png(cover)


def title_lines(draw, name, size):
    """"name-English" as fitted lines: one if it fits at 80% of size or more, else
    "name-" and "English", both in the size the longer fits, so a name is never split."""
    line = fit(draw, f"{name}-English", size, serif)
    if line[1].size >= size * 0.8:
        return [line]
    _, font = fit(draw, f"{name}-", size, serif)
    return [(f"{name}-", font), ("English", font)]


def labelled_cover(heading, lines):
    """PNG bytes of a cover that says it is a test book: heading on a red band, then
    lines (the language, the build time)."""
    cover = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(cover)
    draw.rectangle((0, 300, WIDTH, 560), fill=RED)
    centre(draw, heading, 380, 110, "white", ImageFont.load_default)
    y = 680
    for line in lines:
        y = centre(draw, line, y, 70, GREY, ImageFont.load_default) + 30
    return png(cover)


def serif(size):
    return ImageFont.truetype(TEMPLATES.joinpath("DejaVuSerif.ttf").open("rb"), size)


def centre(draw, text, top, size, fill, font_of):
    """Draw text in font_of(size), shrunk to fit, centred with its ink starting at top;
    return the y its ink ends at."""
    return place(draw, fit(draw, text, size, font_of), top, fill)


def fit(draw, text, size, font_of):
    """(text, font): font_of(size), shrunk until text fits between the margins."""
    font = font_of(size)
    while draw.textlength(text, font=font) > WIDTH - 2 * MARGIN:
        size -= 4
        font = font_of(size)
    return text, font


def ink_height(line):
    text, font = line
    _, top, _, bottom = font.getbbox(text)
    return bottom - top


def place(draw, line, top, fill):
    """Draw a fitted line centred across the cover with its ink starting at top; return
    the y its ink ends at."""
    text, font = line
    left, ink_top, right, bottom = font.getbbox(text)
    draw.text(((WIDTH - (right - left)) / 2 - left, top - ink_top), text, font=font, fill=fill)
    return top + bottom - ink_top


def png(image):
    """A greyscale-and-red image in 64 colours: small enough to stay under kindling's
    127 KB image warning."""
    out = io.BytesIO()
    image.quantize(64).save(out, "PNG", optimize=True)
    return out.getvalue()
