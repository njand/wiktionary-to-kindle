import os

from ..utils import TEMPLATES


class HTMLPage:
    def __init__(self, max_lines=1000, output_fp_prefix=""):
        self.max_lines = max_lines
        self.entry_count = 0

        self.output_fp_prefix = output_fp_prefix
        self.index = 0
        self.output_fp = None
        self.update_output_fp()

        self.header = (
            TEMPLATES.joinpath("html_header.txt").read_text("utf-8").split("\n")
        )
        self.footer = (
            TEMPLATES.joinpath("html_footer.txt").read_text("utf-8").split("\n")
        )

        self.html_lines = list(self.header)

    def update_output_fp(self):
        self.output_fp = f"{self.output_fp_prefix}{self.index:04}.xhtml"

    def get_filename(self):
        """Return the filename without the base directory"""
        return os.path.basename(self.output_fp)

    def add_lines(self, lines: list):
        if not lines:
            return

        self.html_lines.extend(lines)
        self.html_lines.append("<hr/>")
        self.entry_count += 1

        if len(self.html_lines) >= self.max_lines:
            self.write()

    def write(self):
        if self.entry_count == 0:
            return

        self.html_lines.extend(self.footer)
        with open(self.output_fp, "w", encoding="utf-8") as f:
            f.write("\n".join(self.html_lines))

        self.html_lines = list(self.header)
        self.entry_count = 0
        self.index += 1
        self.update_output_fp()
