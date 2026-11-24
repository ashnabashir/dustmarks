# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- Table and Markdown output now show owners, as in `TODO(ada)`.
- `scan(now=...)` accepts a datetime without a timezone and treats it as UTC.
- Docs: running without paths scans the current folder, and the CI example
  uses `actions/checkout@v7`.

## [0.1.0] - 2026-11-24

### Added

- `dustmarks` command that lists TODO, FIXME, HACK and XXX comments with their
  author and age from `git blame`, oldest first.
- Filters for age, author and tag, sorting, limits, and path arguments.
- Table, Markdown and JSON output.
- `--fail-older-than` for CI.
- `dustmarks.scan()` Python API.
