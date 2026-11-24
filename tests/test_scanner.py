import time

import pytest

from dustmarks.scanner import Found, build_pattern, find_in_lines, split_lines

PATTERN = build_pattern()


def find(line: str) -> Found | None:
    return next(find_in_lines([line], PATTERN), None)


@pytest.mark.parametrize(
    ("line", "tag", "text"),
    [
        ("# TODO: handle empty input", "TODO", "handle empty input"),
        ("x = 1  # FIXME off by one", "FIXME", "off by one"),
        ("// HACK - remove after v2", "HACK", "remove after v2"),
        ("/* XXX: why is this here? */", "XXX", "why is this here?"),
        (" * TODO document return value", "TODO", "document return value"),
        ("<!-- TODO: add screenshots -->", "TODO", "add screenshots"),
        ("-- TODO index this column", "TODO", "index this column"),
        ("SELECT 1 -- FIXME slow", "FIXME", "slow"),
        ("; TODO lisp style", "TODO", "lisp style"),
        ("% TODO cite the paper", "TODO", "cite the paper"),
        ("# TODO", "TODO", ""),
        ("#TODO no space", "TODO", "no space"),
        ("## TODO doubled hash", "TODO", "doubled hash"),
        ("/// TODO doc comment", "TODO", "doc comment"),
        ("//! FIXME crate docs", "FIXME", "crate docs"),
        ("/** TODO: javadoc */", "TODO", "javadoc"),
        (";;; TODO lisp heading", "TODO", "lisp heading"),
        ("--- FIXME lua", "FIXME", "lua"),
        ("#: TODO sphinx comment", "TODO", "sphinx comment"),
        ("url = 'https://example.com'  # TODO: move to config", "TODO", "move to config"),
    ],
)
def test_finds_markers_in_comments(line: str, tag: str, text: str) -> None:
    found = find(line)
    assert found is not None
    assert (found.tag, found.text, found.owner) == (tag, text, None)


def test_reads_owner_in_parentheses() -> None:
    found = find("# TODO(ada): rename this")
    assert found == Found(line=1, tag="TODO", owner="ada", text="rename this")


@pytest.mark.parametrize(
    "line",
    [
        'print("TODO")',
        "todo = load_todos()",
        "# todo lowercase is prose, not a marker",
        "# TODOS are plural here",
        "# MY_TODO is a variable name",
        "# XXXL shirt size",
        "x = a--b  TODO",
        '# strings such as print("TODO") are ignored',
        "# see the TODO list in the wiki",
        "",
    ],
)
def test_ignores_non_markers(line: str) -> None:
    assert find(line) is None


def test_custom_tags() -> None:
    pattern = build_pattern(["NOTE", "OPTIMIZE"])
    lines = ["# NOTE keep in sync", "# TODO not requested", "# OPTIMIZE: cache"]
    assert [(f.line, f.tag) for f in find_in_lines(lines, pattern)] == [
        (1, "NOTE"),
        (3, "OPTIMIZE"),
    ]


def test_prefers_longest_overlapping_tag() -> None:
    pattern = build_pattern(["TODO", "TODO-LATER"])
    found = next(find_in_lines(["# TODO-LATER: tidy"], pattern))
    assert (found.tag, found.text) == ("TODO-LATER", "tidy")


@pytest.mark.parametrize("tags", [[], [""], ["TO DO"], ["1TODO"], ["TODO|.*"]])
def test_rejects_invalid_tags(tags: list[str]) -> None:
    with pytest.raises(ValueError):
        build_pattern(tags)


def test_long_lines_stay_fast() -> None:
    line = "x = '" + "http://a/" * 20000 + "' # TODO: finally"
    found = find(line)
    assert found is not None and found.text == "finally"
    for filler in ("/", "#", "-", " --", "/*", "*", "# ", "; ", " "):
        start = time.perf_counter()
        assert find(filler * 100_000) is None
        assert time.perf_counter() - start < 1, filler


def test_split_lines_matches_git_numbering() -> None:
    text = "one\r\ntwo\x0bstill two\x0cand two\u2028two\nthree\n"
    assert split_lines(text) == ["one", "two\x0bstill two\x0cand two\u2028two", "three"]
    assert split_lines("no newline at end") == ["no newline at end"]
    assert split_lines("") == []
