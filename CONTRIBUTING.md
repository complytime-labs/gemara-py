# Contributing to gemara-py

## Development Setup

```bash
uv sync --dev
task test
task lint
```

## Releasing

Releases are automated via GitHub Actions and PyPI trusted publishers.

1. Merge PRs to `main` -- release-drafter accumulates draft release notes
2. Go to [GitHub Releases](https://github.com/complytime-labs/gemara-py/releases)
3. Review the draft, confirm the tag (e.g., `v0.0.2`), and publish
4. Publishing triggers the PyPI publish workflow

### TestPyPI

To publish a test release, go to Actions > "Publish to TestPyPI" > Run workflow.

## Maintainer Setup

### GitHub Environments

Create two environments in repo Settings > Environments:

- `pypi`
- `testpypi`

### Trusted Publisher Setup (one-time)

On [pypi.org](https://pypi.org/manage/project/gemara-py/settings/publishing/)
and [test.pypi.org](https://test.pypi.org/manage/project/gemara-py/settings/publishing/),
add a trusted publisher with:

- **Owner:** `complytime-labs`
- **Repository:** `gemara-py`
- **Workflow:** `publish-pypi.yml` (PyPI) or `publish-testpypi.yml` (TestPyPI)
- **Environment:** `pypi` or `testpypi`
