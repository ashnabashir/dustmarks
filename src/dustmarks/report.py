"""Render marks as a terminal table, Markdown, or JSON."""

import json
from collections import Counter
from collections.abc import Sequence

from dustmarks.core import Mark

_MAX_TEXT = 70


def human_age(days: int) -> str:
    if days < 1:
        return "today"
    if days < 60:
        return f"{days}d"
    if days < 730:
        return f"{days // 30}mo"
    return f"{days // 365}y"


def _who(mark: Mark) -> str:
    if not mark.committed:
        return "(uncommitted)"
    return mark.author or mark.email or "(unknown)"


def _tag(mark: Mark) -> str:
    return f"{mark.tag}({mark.owner})" if mark.owner else mark.tag


def _shorten(text: str, limit: int = _MAX_TEXT) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def summary(marks: Sequence[Mark], shown: int | None = None) -> str:
    """Describe ``marks``; ``shown`` is how many of them were listed, if fewer."""
    if not marks:
        return "No TODO-style comments found."
    files = len({m.path for m in marks})
    counts = Counter(m.tag for m in marks)
    by_tag = ", ".join(f"{count} {tag}" for tag, count in sorted(counts.items()))
    oldest = max(marks, key=lambda m: m.age_days)
    mark_word = "mark" if len(marks) == 1 else "marks"
    file_word = "file" if files == 1 else "files"
    text = (
        f"{len(marks)} {mark_word} in {files} {file_word} ({by_tag}). "
        f"Oldest: {human_age(oldest.age_days)} at {oldest.location}."
    )
    if shown is not None and shown < len(marks):
        text += f" Showing {shown} of {len(marks)}."
    return text


def format_table(marks: Sequence[Mark], total: Sequence[Mark] | None = None) -> str:
    """Render ``marks``; ``total`` is the full result when ``marks`` is a subset."""
    every = marks if total is None else total
    if not marks:
        return summary(every, 0)
    header = ("AGE", "TAG", "AUTHOR", "LOCATION", "TEXT")
    rows = [(human_age(m.age_days), _tag(m), _who(m), m.location, _shorten(m.text)) for m in marks]
    widths = [max(len(row[i]) for row in [header, *rows]) for i in range(len(header) - 1)]

    def render(row: Sequence[str]) -> str:
        cells = [cell.ljust(width) for cell, width in zip(row, widths, strict=False)]
        return "  ".join([*cells, row[-1]]).rstrip()

    return "\n".join(
        [render(header), *(render(row) for row in rows), "", summary(every, len(marks))]
    )


def _md(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")


def format_markdown(marks: Sequence[Mark], total: Sequence[Mark] | None = None) -> str:
    every = marks if total is None else total
    if not marks:
        return summary(every, 0)
    lines = [
        "| Age | Tag | Author | Location | Text |",
        "| --- | --- | --- | --- | --- |",
    ]
    for m in marks:
        lines.append(
            f"| {human_age(m.age_days)} | {_md(_tag(m))} | {_md(_who(m))} "
            f"| {_md(m.location)} | {_md(m.text)} |"
        )
    return "\n".join([*lines, "", summary(every, len(marks))])


def format_json(marks: Sequence[Mark], total: Sequence[Mark] | None = None) -> str:
    del total
    return json.dumps(
        [
            {
                "path": m.path,
                "line": m.line,
                "tag": m.tag,
                "owner": m.owner,
                "text": m.text,
                "author": m.author,
                "email": m.email,
                "commit": m.commit,
                "date": m.date.isoformat() if m.date else None,
                "age_days": m.age_days,
            }
            for m in marks
        ],
        indent=2,
        ensure_ascii=False,
    )


FORMATTERS = {
    "table": format_table,
    "markdown": format_markdown,
    "json": format_json,
}
