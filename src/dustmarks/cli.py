import argparse
import io
import os
import sys
from collections.abc import Sequence

from dustmarks import __version__
from dustmarks.core import scan, sort_marks
from dustmarks.git import GitError
from dustmarks.report import FORMATTERS
from dustmarks.scanner import DEFAULT_TAGS, TAG_NAME


def _days(value: str) -> int:
    try:
        days = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected a whole number of days, got {value!r}"
        ) from None
    if days < 0:
        raise argparse.ArgumentTypeError("days must be 0 or more")
    return days


def _positive(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a whole number, got {value!r}") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return number


def _tag(value: str) -> str:
    if not TAG_NAME.fullmatch(value):
        raise argparse.ArgumentTypeError(
            f"invalid tag {value!r}: use letters, digits, '_' or '-', starting with a letter"
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dustmarks",
        description=(
            "Find TODO, FIXME, HACK and XXX comments in a git repository and show "
            "how long each one has been waiting, and who wrote it."
        ),
        epilog="Exit codes: 0 success, 1 --fail-older-than matched, 2 usage or git error.",
    )
    parser.add_argument(
        "paths", nargs="*", help="limit the scan to these files or folders (git pathspecs)"
    )
    parser.add_argument(
        "-C",
        "--repo",
        default=".",
        metavar="DIR",
        help="run as if started in DIR (default: current folder)",
    )
    parser.add_argument(
        "-t",
        "--tag",
        dest="tags",
        action="append",
        type=_tag,
        metavar="TAG",
        help=f"marker to look for; repeat for several (default: {', '.join(DEFAULT_TAGS)})",
    )
    parser.add_argument(
        "--older-than", type=_days, metavar="DAYS", help="only show marks older than DAYS"
    )
    parser.add_argument(
        "--author", metavar="TEXT", help="only show marks whose author name or email contains TEXT"
    )
    parser.add_argument(
        "-f", "--format", choices=sorted(FORMATTERS), default="table", help="output format"
    )
    parser.add_argument(
        "--sort", choices=["age", "path"], default="age", help="oldest first, or by file"
    )
    parser.add_argument("-n", "--limit", type=_positive, metavar="N", help="show at most N marks")
    parser.add_argument(
        "--fail-older-than",
        type=_days,
        metavar="DAYS",
        help="exit with code 1 if any shown mark is older than DAYS (for CI)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(errors="replace")

    try:
        marks = scan(args.repo, args.paths, tags=args.tags or DEFAULT_TAGS)
    except GitError as exc:
        print(f"dustmarks: {exc}", file=sys.stderr)
        return 2

    if args.older_than is not None:
        marks = [m for m in marks if m.age_days > args.older_than]
    if args.author:
        needle = args.author.casefold()
        marks = [
            m
            for m in marks
            if needle in (m.author or "").casefold() or needle in (m.email or "").casefold()
        ]
    marks = sort_marks(marks, args.sort)

    stale = []
    if args.fail_older_than is not None:
        stale = [m for m in marks if m.age_days > args.fail_older_than]

    shown = marks[: args.limit] if args.limit else marks
    try:
        print(FORMATTERS[args.format](shown, marks))
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 1 if stale else 0

    if stale:
        word = "mark is" if len(stale) == 1 else "marks are"
        print(
            f"dustmarks: {len(stale)} {word} older than {args.fail_older_than} days",
            file=sys.stderr,
        )
        return 1
    return 0
