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
        self.templates = [
            EtymologyTemplate(
                template.get("name", ""),
                transliterate(template.get("expansion", "")),
                template.get("args", {}),
            )
            for template in etymology_templates
            if template.get("expansion")
        ]
        self.etymology_templates = [t.expansion for t in self.templates]


# Templates naming an ancestor: Latin got the word from args 2 (a language) as args 3
ANCESTOR = {"inh", "inh+", "der", "der+", "bor", "bor+", "lbor", "slbor", "ubor"}
BORROWED = {"bor", "bor+", "lbor", "slbor", "ubor"}
# Templates naming a word in args 2 (a cognate, a mention), or several from args 2 on
MENTION = {"cog", "noncog", "m", "l", "m+", "mention", "cognate"}
AFFIXES = {"af", "affix", "prefix", "suffix", "compound", "confix", "surf"}


class EtymologyTemplate:
    def __init__(self, name, expansion, args):
        self.name = name
        self.expansion = expansion
        self.args = args

    @property
    def terms(self):
        """The words the template cites, which a dictionary sets in italics."""
        # The word, or when it is empty the form to display instead (der la ine-pro "" *moh₁-)
        if self.name in ANCESTOR:
            keys = ["3"] if self.args.get("3") else ["4"]
        elif self.name in MENTION:
            keys = ["2"] if self.args.get("2") else ["3"]
        elif self.name in AFFIXES:
            keys = [k for k in self.args if k.isdigit() and int(k) >= 2]
        else:
            return []
        terms = []
        for key in keys:
            term = self.args.get(key, "")
            # A word in a script without a font is shown by its transliteration
            if re.search(f"[{NO_FONT}]", term) and self.args.get("tr"):
                term = ("*" if term.startswith("*") else "") + self.args["tr"]
            if term:
                terms.append(term)
        return terms
