import os
import subprocess
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def isolated_git(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Keep the developer's global git config (signing, hooks, names) out of tests."""
    empty = tmp_path_factory.mktemp("gitconfig") / "config"
    empty.write_text("")
    keys = ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")
    saved = {key: os.environ.get(key) for key in keys}
    os.environ["GIT_CONFIG_GLOBAL"] = str(empty)
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    yield
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class Repo:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str, env: dict[str, str] | None = None) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.path,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, **(env or {})},
        )
        return result.stdout

    def write(self, name: str, content: str | bytes) -> Path:
        path = self.path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="")
        return path

    def commit(self, message: str, date: str, author: str = "Ada Lovelace") -> None:
        email = author.lower().replace(" ", ".") + "@example.com"
        self.git("add", "-A")
        self.git(
            "commit",
            "-q",
            "-m",
            message,
            env={
                "GIT_AUTHOR_NAME": author,
                "GIT_AUTHOR_EMAIL": email,
                "GIT_COMMITTER_NAME": author,
                "GIT_COMMITTER_EMAIL": email,
                "GIT_AUTHOR_DATE": date,
                "GIT_COMMITTER_DATE": date,
            },
        )


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    path = tmp_path / "project"
    path.mkdir()
    return Repo(path)
