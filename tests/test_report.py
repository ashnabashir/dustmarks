import json
from datetime import datetime, timezone

import pytest

from dustmarks.core import Mark
from dustmarks.report import format_json, format_markdown, format_table, human_age, summary


def make(**overrides: object) -> Mark:
    values: dict[str, object] = {
        "path": "src/app.py",
        "line": 10,
        "tag": "TODO",
        "owner": None,
        "text": "handle errors",
        "author": "Ada Lovelace",
        "email": "ada@example.com",
        "commit": "a" * 40,
        "date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "age_days": 400,
    }
    values.update(overrides)
    return Mark(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("days", "expected"),
    [(0, "today"), (1, "1d"), (59, "59d"), (60, "2mo"), (729, "24mo"), (730, "2y"), (1500, "4y")],
)
def test_human_age(days: int, expected: str) -> None:
    assert human_age(days) == expected


def test_empty_outputs() -> None:
    assert format_table([]) == "No TODO-style comments found."
    assert format_markdown([]) == "No TODO-style comments found."
    assert json.loads(format_json([])) == []


def test_summary_counts_tags_files_and_oldest() -> None:
    marks = [
        make(),
        make(path="b.py", tag="FIXME", age_days=900, line=2),
        make(path="b.py", line=5, age_days=3),
    ]
    assert summary(marks) == "3 marks in 2 files (1 FIXME, 2 TODO). Oldest: 2y at b.py:2."
    assert summary([make()]) == "1 mark in 1 file (1 TODO). Oldest: 13mo at src/app.py:10."


def test_table_aligns_columns_and_shortens_text() -> None:
    long_text = "word " * 30
    table = format_table([make(), make(commit=None, author=None, text=long_text, age_days=0)])
    header, first, second = table.splitlines()[:3]
    assert header.split() == ["AGE", "TAG", "AUTHOR", "LOCATION", "TEXT"]
    assert first.index("src/app.py") == header.index("LOCATION")
    assert "(uncommitted)" in second
    assert second.endswith("…") and len(second.split("src/app.py:10")[1].strip()) == 70


def test_table_falls_back_to_email_then_unknown() -> None:
    table = format_table([make(author=None), make(author=None, email=None)])
    assert "ada@example.com" in table
    assert "(unknown)" in table


def test_markdown_escapes_special_characters() -> None:
    output = format_markdown([make(text="a | b `code` c\\d", path="we|ird.py")])
    row = output.splitlines()[2]
    assert row == "| 13mo | TODO | Ada Lovelace | we\\|ird.py:10 | a \\| b \\`code\\` c\\\\d |"


def test_owner_is_shown_next_to_the_tag() -> None:
    table = format_table([make(owner="ada")])
    assert table.splitlines()[1].split()[:2] == ["13mo", "TODO(ada)"]
    row = format_markdown([make(owner="a|b")]).splitlines()[2]
    assert row.startswith("| 13mo | TODO(a\\|b) | Ada Lovelace |")


def test_summary_mentions_hidden_marks() -> None:
    every = [make(), make(line=11), make(line=12)]
    assert format_table(every[:1], every).endswith("Showing 1 of 3.")
    assert format_markdown(every[:2], every).endswith("Showing 2 of 3.")
    assert "Showing" not in format_table(every, every)


def test_json_has_all_fields() -> None:
    [record] = json.loads(format_json([make(owner="ada", text="café")]))
    assert record == {
        "path": "src/app.py",
        "line": 10,
        "tag": "TODO",
        "owner": "ada",
        "text": "café",
        "author": "Ada Lovelace",
        "email": "ada@example.com",
        "commit": "a" * 40,
        "date": "2024-01-01T00:00:00+00:00",
        "age_days": 400,
    }
    assert json.loads(format_json([make(date=None, commit=None)]))[0]["date"] is None
