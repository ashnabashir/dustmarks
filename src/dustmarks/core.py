"""Scan a repository for markers and attach their git history."""

import os
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dustmarks.git import UNCOMMITTED, BlameInfo, blame_lines, list_files, repo_root
from dustmarks.scanner import DEFAULT_TAGS, Found, build_pattern, find_in_lines, split_lines

MAX_FILE_BYTES = 2_000_000
_BINARY_SNIFF_BYTES = 8192
_MAX_WORKERS = min(8, os.cpu_count() or 1)


@dataclass(frozen=True)
class Mark:
    """A TODO-style comment and who added it, when."""

    path: str
    line: int
    tag: str
    owner: str | None
    text: str
    author: str | None
    email: str | None
    commit: str | None
    date: datetime | None
    age_days: int

    @property
    def location(self) -> str:
        return f"{self.path}:{self.line}"

    @property
    def committed(self) -> bool:
        return self.commit is not None


def scan(
    start: str | Path = ".",
    pathspecs: Sequence[str] = (),
    tags: Sequence[str] = DEFAULT_TAGS,
    now: datetime | None = None,
) -> list[Mark]:
    """Return every marker in the repository containing ``start``, oldest first.

    ``pathspecs`` limit the scan the same way they limit ``git ls-files`` run
    from ``start``. Raises :class:`dustmarks.GitError` outside a git repository.
    """
    start_path = Path(start).resolve()
    root = repo_root(start_path)
    pattern = build_pattern(tags)
    now = now or datetime.now(timezone.utc)

    pending: list[tuple[str, list[Found]]] = []
    for relative in list_files(start_path, pathspecs):
        text = _read_text(root / relative)
        if text is None:
            continue
        found = list(find_in_lines(split_lines(text), pattern))
        if found:
            pending.append((relative, found))

    def blame(entry: tuple[str, list[Found]]) -> dict[int, BlameInfo]:
        relative, found = entry
        return blame_lines(root, relative, (item.line for item in found))

    # Each git blame is a separate process, so threads run them in parallel.
    workers = min(_MAX_WORKERS, len(pending)) or 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        blames = list(pool.map(blame, pending))

    marks: list[Mark] = []
    for (relative, found), blamed in zip(pending, blames, strict=True):
        for item in found:
            info = blamed.get(item.line, UNCOMMITTED)
            age = max(0, (now - info.date).days) if info.date else 0
            marks.append(
                Mark(
                    path=relative,
                    line=item.line,
                    tag=item.tag,
                    owner=item.owner,
                    text=item.text,
                    author=info.author,
                    email=info.email,
                    commit=info.commit,
                    date=info.date,
                    age_days=age,
                )
            )
    return sort_marks(marks, "age")


def sort_marks(marks: Sequence[Mark], key: str) -> list[Mark]:
    if key == "age":
        return sorted(marks, key=lambda m: (-m.age_days, m.path, m.line))
    if key == "path":
        return sorted(marks, key=lambda m: (m.path, m.line))
    raise ValueError(f"unknown sort key {key!r}")


def _read_text(path: Path) -> str | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:_BINARY_SNIFF_BYTES]:
        return None
    return data.decode("utf-8", errors="replace")
