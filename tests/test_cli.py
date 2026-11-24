import json
from pathlib import Path

import pytest

from dustmarks.cli import main

from .conftest import Repo


@pytest.fixture
def project(repo: Repo) -> Repo:
    repo.write("old.py", "# TODO: written long ago\n")
    repo.commit("old", "2020-01-01T00:00:00+00:00", author="Ada Lovelace")
    repo.write("new.py", "# FIXME: recent\n")
    repo.commit("new", "2099-01-01T00:00:00+00:00", author="Grace Hopper")
    return repo


def run(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = main(list(args))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_table_output(project: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "-C", str(project.path))
    assert code == 0
    lines = out.splitlines()
    assert lines[0].split() == ["AGE", "TAG", "AUTHOR", "LOCATION", "TEXT"]
    assert "old.py:1" in lines[1] and "Ada Lovelace" in lines[1]
    assert "new.py:1" in lines[2]
    assert lines[-1].startswith("2 marks in 2 files")


def test_json_output_and_filters(project: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "-C", str(project.path), "-f", "json", "--older-than", "365")
    assert code == 0
    assert [m["path"] for m in json.loads(out)] == ["old.py"]

    _, out, _ = run(capsys, "-C", str(project.path), "-f", "json", "--author", "GRACE")
    assert [m["path"] for m in json.loads(out)] == ["new.py"]

    _, out, _ = run(capsys, "-C", str(project.path), "-f", "json", "--author", "lovelace@example")
    assert [m["path"] for m in json.loads(out)] == ["old.py"]

    _, out, _ = run(capsys, "-C", str(project.path), "-f", "json", "-t", "FIXME")
    assert [m["tag"] for m in json.loads(out)] == ["FIXME"]


def test_sort_and_limit(project: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = run(capsys, "-C", str(project.path), "-f", "json", "--sort", "path")
    assert [m["path"] for m in json.loads(out)] == ["new.py", "old.py"]

    _, out, _ = run(capsys, "-C", str(project.path), "-f", "json", "-n", "1")
    assert [m["path"] for m in json.loads(out)] == ["old.py"]

    _, out, _ = run(capsys, "-C", str(project.path), "-n", "1")
    assert out.splitlines()[-1].startswith("2 marks in 2 files")
    assert out.rstrip().endswith("Showing 1 of 2.")


def test_markdown_output(project: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "-C", str(project.path), "-f", "markdown")
    assert code == 0
    assert out.startswith("| Age | Tag | Author | Location | Text |")


def test_fail_older_than(project: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "-C", str(project.path), "--fail-older-than", "365")
    assert code == 1
    assert "old.py:1" in out
    assert err.strip() == "dustmarks: 1 mark is older than 365 days"

    code, _, err = run(capsys, "-C", str(project.path), "--fail-older-than", "100000")
    assert (code, err) == (0, "")


def test_fail_older_than_counts_marks_hidden_by_limit(
    project: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = run(
        capsys, "-C", str(project.path), "--sort", "path", "-n", "1", "--fail-older-than", "365"
    )
    assert code == 1
    assert "1 mark is older" in err


def test_paths_limit_the_scan(project: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = run(capsys, "-C", str(project.path), "-f", "json", "new.py")
    assert [m["path"] for m in json.loads(out)] == ["new.py"]


def test_no_marks(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    repo.write("clean.py", "x = 1\n")
    repo.commit("clean", "2024-01-01T00:00:00+00:00")
    code, out, _ = run(capsys, "-C", str(repo.path))
    assert (code, out.strip()) == (0, "No TODO-style comments found.")


def test_not_a_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "-C", str(tmp_path))
    assert (code, out) == (2, "")
    assert err.startswith("dustmarks: ") and "not a git repository" in err


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--tag", "TO DO"], "invalid tag"),
        (["--older-than", "-1"], "days must be 0 or more"),
        (["--older-than", "soon"], "whole number of days"),
        (["--limit", "0"], "must be 1 or more"),
        (["--limit", "x"], "expected a whole number"),
        (["--format", "xml"], "invalid choice"),
    ],
)
def test_invalid_arguments(
    capsys: pytest.CaptureFixture[str], args: list[str], message: str
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(args)
    assert exc_info.value.code == 2
    assert message in capsys.readouterr().err
