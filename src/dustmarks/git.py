"""Thin wrappers around the git command line."""

import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_UNCOMMITTED_SHA = "0" * 40
_BLAME_BATCH = 400


class GitError(Exception):
    """Raised when a git command fails or git is unavailable."""


@dataclass(frozen=True)
class BlameInfo:
    commit: str | None
    author: str | None
    email: str | None
    date: datetime | None


UNCOMMITTED = BlameInfo(commit=None, author=None, email=None, date=None)


def run_git(cwd: Path, args: Sequence[str]) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH") from exc
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise GitError(message or f"git {args[0]} failed with exit code {result.returncode}")
    return result.stdout


def repo_root(start: Path) -> Path:
    if not start.is_dir():
        raise GitError(f"{start} is not a directory")
    output = run_git(start, ["rev-parse", "--show-toplevel"])
    return Path(output.decode("utf-8").strip())


def list_files(start: Path, pathspecs: Sequence[str] = ()) -> list[str]:
    """Return tracked and untracked-but-not-ignored files, relative to the repo root."""
    output = run_git(
        start,
        [
            "ls-files",
            "-z",
            "--full-name",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            *pathspecs,
        ],
    )
    names = {name.decode("utf-8", "surrogateescape") for name in output.split(b"\0") if name}
    return sorted(names)


def blame_lines(root: Path, path: str, line_numbers: Iterable[int]) -> dict[int, BlameInfo]:
    """Blame the working-tree version of ``path`` for the given 1-based lines.

    Lines that git cannot attribute to a commit (new files, unsaved edits, or a
    repository without commits) are missing from the result.
    """
    numbers = sorted(set(line_numbers))
    result: dict[int, BlameInfo] = {}
    # Batches keep the command line well under Windows' length limit.
    for start in range(0, len(numbers), _BLAME_BATCH):
        args = ["blame", "--line-porcelain"]
        for number in numbers[start : start + _BLAME_BATCH]:
            args += ["-L", f"{number},{number}"]
        args += ["--", path]
        try:
            output = run_git(root, args)
        except GitError:
            return result
        result.update(parse_porcelain(output))
    return result


def parse_porcelain(output: bytes) -> dict[int, BlameInfo]:
    result: dict[int, BlameInfo] = {}
    entry: dict[str, str] | None = None
    for raw in output.split(b"\n"):
        if entry is None:
            if not raw:
                continue
            sha, _, rest = raw.decode("utf-8", "replace").partition(" ")
            entry = {"sha": sha, "line": rest.split(" ")[1]}
        elif raw.startswith(b"\t"):
            result[int(entry["line"])] = _to_info(entry)
            entry = None
        else:
            key, _, value = raw.decode("utf-8", "replace").partition(" ")
            entry[key] = value
    return result


def _to_info(entry: dict[str, str]) -> BlameInfo:
    if entry["sha"] == _UNCOMMITTED_SHA:
        return UNCOMMITTED
    email = entry.get("author-mail", "").strip().removeprefix("<").removesuffix(">")
    timestamp = entry.get("author-time")
    return BlameInfo(
        commit=entry["sha"],
        author=entry.get("author") or None,
        email=email or None,
        date=datetime.fromtimestamp(int(timestamp), tz=timezone.utc) if timestamp else None,
    )
