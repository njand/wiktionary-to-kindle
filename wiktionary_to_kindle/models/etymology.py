import re

from ..utils import normalize

# Scripts a Kindle has no font for: everything outside the Basic Multilingual Plane
# (Gothic, Old Italic, Avestan, cuneiform, Linear B, Phoenician, ...) and Runic. Their
# words show as empty boxes, but Wiktionary writes nearly all of them with a
# transliteration: 𐌰𐍄𐌹𐍃𐌺 (atisk).
NO_FONT = f"{chr(0x10000)}-{chr(0x10FFFF)}{chr(0x16A0)}-{chr(0x16FF)}"
# Joiners and direction marks Wiktionary puts inside such words
INSIDE = f"{chr(0x200B)}-{chr(0x200F)}{chr(0x202A)}-{chr(0x202E)}"
TRANSLITERATED = re.compile(
    rf"\*?[{NO_FONT}](?:[{NO_FONT}{INSIDE} \-]*[{NO_FONT}{INSIDE}])? \(([^()]*)\)"
)


def transliterate(text):
    """text with each word in a script a Kindle cannot show replaced by its
    transliteration: "Gothic 𐌰𐍄𐌹𐍃𐌺 (atisk)" becomes "Gothic atisk", and
    "𐁁𐀓𐀠𐀴𐀍 (a3-ku-pi-ti-jo, “Egyptian”)" becomes "a3-ku-pi-ti-jo (“Egyptian”)"."""

    def replace(match):
        translit, _, rest = match.group(1).partition(", ")
        return f"{translit} ({rest})" if rest else translit

    return TRANSLITERATED.sub(replace, text)


def strip_tree(text, word):
    """text without the etymology tree Wiktionary puts before some etymologies: a line
    "Etymology tree", then one line per ancestor ("Proto-Italic *ap"), ending with the
    word itself ("Latin abyssālis"). Left whole when that last line is not found."""
    if not text or not text.startswith("Etymology tree\n"):
        return text
    lines = text.split("\n")[1:]
    plain = normalize(word, lowercase=True)
    ends = [
        i
        for i, line in enumerate(lines)
        if normalize(line, lowercase=True).split(" ")[-1].lstrip("*") == plain
    ]
    if not ends or ends[-1] + 1 == len(lines):
        return text
    return "\n".join(lines[ends[-1] + 1 :])


class Etymology:
    def __init__(self, etymology_text, etymology_templates, word=""):
        self.etymology_text = etymology_text and transliterate(
            strip_tree(etymology_text, word)
        )
        self.etymology_templates = self.process_templates(etymology_templates)

    def process_templates(self, etymology_templates):
        processed_templates = []
        for template in etymology_templates:
            expansion = transliterate(template.get("expansion", ""))
            if len(expansion) > 0:
                processed_templates.append(expansion)
        return processed_templates
