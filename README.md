# dustmarks

[![CI](https://github.com/ashnabashir/dustmarks/actions/workflows/ci.yml/badge.svg)](https://github.com/ashnabashir/dustmarks/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Find the TODOs that are gathering dust.** dustmarks lists every `TODO`,
`FIXME`, `HACK` and `XXX` comment in a git repository, uses `git blame` to show
who wrote each one and how long ago, and puts the oldest first.

```console
$ dustmarks
AGE    TAG    AUTHOR         LOCATION                  TEXT
4y     TODO   Ada Lovelace   src/billing/invoice.py:2  handle refunds in other currencies
13mo   FIXME  Grace Hopper   web/api/client.ts:2       retry on 503 instead of failing
21d    HACK   Linus Ito      scripts/deploy.sh:2       remove after the new runner ships
today  TODO   (uncommitted)  src/app.py:2              add --dry-run

4 marks in 4 files (1 FIXME, 1 HACK, 2 TODO). Oldest: 4y at src/billing/invoice.py:2.
```

## Why

A `TODO` from last week is a plan. A `TODO` from four years ago is a bug
report nobody filed. dustmarks makes the difference visible, so you can turn
old markers into issues, fix them, or delete them, and keep new ones from
going stale with a CI check.

## Features

- Works on any language: `#`, `//`, `/* */`, `*`, `--`, `<!-- -->`, `;` and `%` comments.
- Only counts a marker when it starts a comment, so `print("TODO")` and
  comments that merely mention a TODO are ignored.
- Shows the author, date and commit of the line that added each marker,
  including edits you haven't committed yet.
- Understands owners: `TODO(ada): ...`.
- Respects `.gitignore` and skips binary and very large files.
- Output as a table, Markdown (for issues and PR comments) or JSON.
- `--fail-older-than DAYS` for CI. No dependencies beyond Python and git.

## Install

Requires Python 3.10 or newer and git.

```bash
pip install git+https://github.com/ashnabashir/dustmarks.git
```

## Usage

```bash
dustmarks                          # the whole repository, oldest first
dustmarks src tests                # only these folders
dustmarks --older-than 365         # markers more than a year old
dustmarks --author grace           # markers written by a matching author or email
dustmarks -t TODO -t NOTE          # choose which tags to look for
dustmarks --sort path -n 20        # first 20 markers, grouped by file
dustmarks -f markdown > TODOS.md   # a Markdown report
dustmarks -f json | jq '.[0]'      # machine-readable output
dustmarks -C ~/code/other-project  # scan another repository
```

| Exit code | Meaning |
| --- | --- |
| 0 | Scan finished. |
| 1 | `--fail-older-than` found markers older than the limit. |
| 2 | Invalid arguments, not a git repository, or git is missing. |

### In CI

Fail the build when a marker has waited more than 180 days:

```yaml
- uses: actions/checkout@v5
  with:
    fetch-depth: 0 # full history so ages are accurate
- run: pip install git+https://github.com/ashnabashir/dustmarks.git
- run: dustmarks --fail-older-than 180
```

A shallow clone makes every line look as new as the latest commit, so
fetch the full history.

### From Python

```python
from dustmarks import scan

for mark in scan(".", tags=["TODO", "FIXME"]):
    print(mark.age_days, mark.author, mark.location, mark.text)
```

`scan()` returns `Mark` objects with `path`, `line`, `tag`, `owner`, `text`,
`author`, `email`, `commit`, `date` and `age_days`.

## Development

```bash
git clone https://github.com/ashnabashir/dustmarks.git
cd dustmarks
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install

pytest                             # tests with coverage
ruff check . && ruff format --check .
mypy
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Project layout

```text
.
├── .github/              # CI workflow, issue forms, PR template
├── src/dustmarks/
│   ├── scanner.py        # finds markers inside comments
│   ├── git.py            # git ls-files and git blame
│   ├── core.py           # scan() and the Mark type
│   ├── report.py         # table, Markdown and JSON output
│   └── cli.py            # the dustmarks command
├── tests/                # unit tests and tests against real git repositories
├── CHANGELOG.md
├── CONTRIBUTING.md
└── pyproject.toml
```

## License

MIT. See [LICENSE](LICENSE).
