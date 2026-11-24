# Contributing

Thanks for helping improve dustmarks.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

You also need git on your `PATH`; the tests create small throwaway
repositories.

## Before opening a pull request

```bash
ruff check . && ruff format --check .
mypy
pytest
```

- Open an issue first for larger changes so we can agree on the approach.
- Keep each pull request focused on one change and include tests.
- New comment styles belong in `src/dustmarks/scanner.py`, with cases in
  `tests/test_scanner.py` for lines that should and should not match.
- Add a line under `[Unreleased]` in `CHANGELOG.md` for user-facing changes.
