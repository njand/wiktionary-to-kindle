"""A release's notes: one table of every dictionary in it, then each one's details folded
away (index and coverage compared with the previous release, the device check)."""

from pathlib import Path

from ..languages import get_language
from . import coverage, stats


def release_notes(current, previous=None, docs=Path("docs"), intro=""):
    """Markdown for the dictionaries whose stats-LANG.json (and coverage-LANG.json/.md,
    prepared-LANG.md) are in the folder current, compared with those in previous."""
    current = Path(current)
    codes = sorted(p.stem.removeprefix("stats-") for p in current.glob("stats-*.json"))
    rows = [
        "| Dictionary | Entries | Words that open | Since latest release | Kindle file |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    details = []
    for code in codes:
        name = get_language(code).name
        new_stats = stats.load(current / f"stats-{code}.json")
        old_stats = _load(previous, f"stats-{code}.json")
        new_cov = _load(current, f"coverage-{code}.json")
        old_cov = _load(previous, f"coverage-{code}.json")

        opens = f"{coverage.opens(new_cov['overall']):.1%}" if new_cov else "–"
        change = "–"  # nothing to compare with
        if new_cov and old_cov:
            points = coverage.opens(new_cov["overall"]) - coverage.opens(
                old_cov["overall"]
            )
            change = f"{points * 100:+.1f} pp".replace("-0.0", "±0.0")
            change = change.replace("+0.0", "±0.0")
        mobi = f"`{code}-wiktionary.mobi`, {new_stats['mobi_bytes'] / 1e6:.0f} MB"
        rows.append(
            f"| {name} | {new_stats['entries']:,} | {opens} | {change} | {mobi} |"
        )

        body = []
        if old_stats:
            body += ["#### Index compared with the latest release", ""]
            body.append(stats.diff(old_stats, new_stats)[0])
        if (current / f"coverage-{code}.md").exists():
            body += ["", "#### Corpus coverage", ""]
            body.append(_read(current / f"coverage-{code}.md"))
        if new_cov and old_cov:
            body += ["", "#### Coverage compared with the latest release", ""]
            body.append(coverage.diff(old_cov, new_cov)[0])
        if (current / f"prepared-{code}.md").exists():
            body += ["", "#### A book prepared with prepare-book (--decide rooted)", ""]
            body.append(_read(current / f"prepared-{code}.md"))
        if body:
            details.append(_fold(f"{name}: index and coverage", body))
        if (docs / f"device-check-{code}.md").exists():
            details.append(
                _fold(
                    f"{name}: device check", [_read(docs / f"device-check-{code}.md")]
                )
            )

    parts = [intro.strip()] if intro.strip() else []
    parts += ["\n".join(rows), *details]
    return "\n\n".join(parts) + "\n"


def _load(folder, name):
    path = Path(folder) / name if folder else None
    return stats.load(path) if path and path.exists() else None


def _read(path):
    return path.read_text(encoding="utf-8").strip()


def _fold(summary, body):
    """body under a summary line GitHub shows closed until it is clicked."""
    return "\n".join(
        [f"<details><summary>{summary}</summary>", "", *body, "", "</details>"]
    )
