"""Compile stage: write the OPF package and run kindling on it to make the .mobi."""

import os
import shutil
import subprocess
from string import Template
from subprocess import CalledProcessError

from .utils import TEMPLATES


def write_opf(files_dir, page_count, dump_date, build_date, version):
    """Write dictionary.opf: the front page, then page_count entry pages."""
    opf_header = Template(TEMPLATES.joinpath("opf_header.txt").read_text("utf-8"))
    html_lines = opf_header.substitute(
        dump_date=dump_date, build_date=build_date, version=version
    ).split("\n")

    for page_num in range(page_count):
        html_lines.append(
            f'<item id="page-{page_num}" href="{page_num:04}.xhtml" media-type="application/xhtml+xml"/>'
        )

    html_lines.extend(["</manifest>", "<spine>", '<itemref idref="front"/>'])
    for page_num in range(page_count):
        html_lines.append(f'<itemref idref="page-{page_num}"/>')

    html_lines.extend(
        [
            "</spine>",
            "<guide>",
            '    <reference type="copyright-page" title="Sources and license" href="front.xhtml"/>',
            '    <reference type="index" title="Dictionary" href="0000.xhtml"/>',
            "</guide>",
            "</package>",
        ]
    )
    with open(os.path.join(files_dir, "dictionary.opf"), "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))


def compile_mobi(kindling, files_dir, output_dir, mobi_name):
    """Run kindling on files_dir/dictionary.opf and move the .mobi into output_dir.

    kindling runs from files_dir, so a relative path to it breaks; pass it absolute or as
    a bare name found on PATH."""
    src_path = os.path.join(files_dir, mobi_name)
    dst_path = os.path.join(output_dir, mobi_name)

    try:
        subprocess.run(
            [kindling, "dictionary.opf", "-o", mobi_name],
            cwd=files_dir,
            check=True,
        )
        if os.path.exists(src_path):
            shutil.move(src_path, dst_path)
    except CalledProcessError as e:
        if os.path.exists(src_path):
            shutil.move(src_path, dst_path)
        else:
            print(
                f"Error compiling MOBI (exit code {e.returncode}). No binary generated."
            )
            raise
