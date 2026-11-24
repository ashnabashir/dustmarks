from datetime import datetime, timezone
from pathlib import Path

import pytest

from dustmarks import GitError, scan
from dustmarks.git import parse_porcelain

from .conftest import NOW, Repo


def test_attaches_author_and_age(repo: Repo) -> None:
    repo.write("app.py", "def main():\n    pass  # TODO: add argument parsing\n")
    repo.commit("first", "2023-01-01T00:00:00+00:00", author="Ada Lovelace")
    repo.write("lib.js", "// FIXME(grace): leaks memory\n")
    repo.commit("second", "2025-12-01T00:00:00+00:00", author="Grace Hopper")

    marks = scan(repo.path, now=NOW)

    assert [(m.location, m.tag, m.author, m.age_days) for m in marks] == [
        ("app.py:2", "TODO", "Ada Lovelace", 1096),
        ("lib.js:1", "FIXME", "Grace Hopper", 31),
    ]
    first = marks[0]
    assert first.email == "ada.lovelace@example.com"
    assert first.date == datetime(2023, 1, 1, tzinfo=timezone.utc)
    assert first.committed and first.commit is not None and len(first.commit) == 40
    assert marks[1].owner == "grace"


def test_blames_the_line_that_added_the_marker(repo: Repo) -> None:
    repo.write("a.py", "x = 1\n")
    repo.commit("old", "2020-01-01T00:00:00+00:00", author="Ada Lovelace")
    repo.write("a.py", "x = 1\n# TODO newer line\n")
    repo.commit("new", "2025-06-01T00:00:00+00:00", author="Grace Hopper")

    [mark] = scan(repo.path, now=NOW)
    assert (mark.line, mark.author) == (2, "Grace Hopper")


def test_uncommitted_and_untracked_marks(repo: Repo) -> None:
    repo.write("a.py", "x = 1\n")
    repo.commit("base", "2024-01-01T00:00:00+00:00")
    repo.write("a.py", "x = 1\n# TODO unsaved edit\n")
    repo.write("new.py", "# HACK brand new file\n")

    marks = scan(repo.path, now=NOW)

    assert {m.location for m in marks} == {"a.py:2", "new.py:1"}
    for mark in marks:
        assert (mark.committed, mark.author, mark.date, mark.age_days) == (False, None, None, 0)


def test_repository_without_commits(repo: Repo) -> None:
    repo.write("a.py", "# TODO first thought\n")
    [mark] = scan(repo.path, now=NOW)
    assert not mark.committed


def test_skips_ignored_binary_deleted_and_large_files(
    repo: Repo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo.write(".gitignore", "build/\n")
    repo.write("build/out.py", "# TODO generated\n")
    repo.write("image.png", b"\x89PNG\0\0# TODO not text")
    repo.write("gone.py", "# TODO deleted later\n")
    repo.write("big.py", "# TODO big file\n")
    repo.write("kept.py", "# TODO keep me\n")
    repo.commit("files", "2024-01-01T00:00:00+00:00")
    (repo.path / "gone.py").unlink()
    monkeypatch.setattr("dustmarks.core.MAX_FILE_BYTES", 15)

    assert [m.path for m in scan(repo.path, now=NOW)] == ["kept.py"]


def test_pathspecs_are_relative_to_start(repo: Repo) -> None:
    repo.write("src/pkg/a.py", "# TODO in package\n")
    repo.write("src/other.py", "# TODO elsewhere\n")
    repo.write("docs/notes.md", "<!-- TODO docs -->\n")
    repo.commit("files", "2024-01-01T00:00:00+00:00")

    assert [m.path for m in scan(repo.path / "src", ["pkg"], now=NOW)] == ["src/pkg/a.py"]
    assert {m.path for m in scan(repo.path / "src", now=NOW)} == {"src/pkg/a.py", "src/other.py"}


def test_handles_crlf_and_unusual_line_breaks(repo: Repo) -> None:
    repo.write("win.py", "a = 1\r\n\x0c\r\n# TODO after form feed\r\n")
    repo.commit("crlf", "2024-01-01T00:00:00+00:00")
    [mark] = scan(repo.path, now=NOW)
    assert (mark.line, mark.text, mark.committed) == (3, "after form feed", True)


def test_many_marks_in_one_file_are_all_blamed(repo: Repo) -> None:
    repo.write("many.py", "".join(f"# TODO item {i}\n" for i in range(1, 1001)))
    repo.commit("many", "2024-01-01T00:00:00+00:00")
    marks = scan(repo.path, now=NOW)
    assert len(marks) == 1000
    assert all(m.committed for m in marks)


def test_custom_tags(repo: Repo) -> None:
    repo.write("a.py", "# NOTE keep\n# TODO skip\n")
    repo.commit("tags", "2024-01-01T00:00:00+00:00")
    assert [m.tag for m in scan(repo.path, tags=["NOTE"], now=NOW)] == ["NOTE"]


def test_outside_a_repository_raises(tmp_path: Path) -> None:
    with pytest.raises(GitError, match="not a git repository"):
        scan(tmp_path)


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(GitError, match="not a directory"):
        scan(tmp_path / "missing")


def test_parse_porcelain_handles_boundary_and_missing_fields() -> None:
    sha = "a" * 40
    output = (
        f"{sha} 1 3 1\nauthor Ada\nauthor-mail <>\nboundary\nfilename x.py\n\t# TODO\n".encode()
    )
    info = parse_porcelain(output)[3]
    assert (info.commit, info.author, info.email, info.date) == (sha, "Ada", None, None)
