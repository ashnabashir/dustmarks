"""Find TODO-style markers inside source code comments."""

import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

DEFAULT_TAGS: tuple[str, ...] = ("TODO", "FIXME", "HACK", "XXX")

TAG_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")

# A marker only counts as the first word of a comment, so code like
# print("TODO") and prose that merely mentions a tag are ignored.
_COMMENT_START = re.compile(r"#+|//+|/\*+|<!--|^\s*\*+|^\s*--+|\s--+|^\s*;+|^\s*%+")
_TRAILING_CLOSERS = re.compile(r"\s*(?:\*/|-->)\s*$")


@dataclass(frozen=True)
class Found:
    line: int
    tag: str
    owner: str | None
    text: str


def build_pattern(tags: Sequence[str] = DEFAULT_TAGS) -> re.Pattern[str]:
    if not tags:
        raise ValueError("at least one tag is required")
    for tag in tags:
        if not TAG_NAME.fullmatch(tag):
            raise ValueError(f"invalid tag {tag!r}: use letters, digits, '_' or '-'")
    alternatives = "|".join(re.escape(tag) for tag in sorted(set(tags), key=len, reverse=True))
    # Nothing allowed before the tag may also start a comment; that keeps
    # matching linear on lines full of "#", "/", "-" or "*".
    return re.compile(
        rf"[\s!:]*(?P<tag>{alternatives})(?![\w-])"
        r"(?:\((?P<owner>[^)]*)\))?[\s:\-]*(?P<text>.*)$"
    )


def find_in_lines(lines: Iterable[str], pattern: re.Pattern[str]) -> Iterator[Found]:
    """Yield markers from ``lines``, numbering lines from 1."""
    for number, line in enumerate(lines, start=1):
        match = None
        for comment in _COMMENT_START.finditer(line):
            match = pattern.match(line, comment.end())
            if match is not None:
                break
        if match is None:
            continue
        owner = (match.group("owner") or "").strip() or None
        text = _TRAILING_CLOSERS.sub("", match.group("text")).strip()
        yield Found(line=number, tag=match.group("tag"), owner=owner, text=text)


def split_lines(text: str) -> list[str]:
    """Split like git does: only on ``\\n``, dropping a trailing ``\\r``."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line.removesuffix("\r") for line in lines]
