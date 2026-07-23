# gemara-py

Gemara types as Pydantic models, generated from the
[Gemara CUE schemas](https://github.com/gemaraproj/gemara).

## Installation

```bash
pip install gemara-py
```

## Usage

```python
# Use latest version (v1.3.0)
from gemara_py import ControlCatalog, EvaluationLog, Policy

# Pin to a specific version
from gemara_py.types.gemara_1_3_0 import ControlCatalog
from gemara_py.types.gemara_1_0_0 import ControlCatalog as ControlCatalogV1

# Parse a YAML file
import yaml

with open("my-catalog.yaml") as f:
    data = yaml.safe_load(f)

catalog = ControlCatalog.model_validate(data)
print(catalog.metadata.id)
```

## Available Versions

| Module | Gemara Spec |
|--------|-------------|
| `gemara_py.types.gemara_1_3_0` | v1.3.0 |
| `gemara_py.types.gemara_1_2_0` | v1.2.0 |
| `gemara_py.types.gemara_1_0_0` | v1.0.0 |

## Regenerating Types

Requires [CUE](https://cuelang.org/) v0.17+, [Task](https://taskfile.dev/) v3+, and development dependencies:

```bash
uv sync --dev
task generate
```

## Development

```bash
uv sync --dev
task test
task lint
```

## Releasing

Releases are automated via GitHub Actions:

1. Merge PRs to `main` -- release-drafter accumulates draft release notes
2. Go to [GitHub Releases](https://github.com/complytime-labs/gemara-py/releases)
3. Review the draft, confirm the tag (e.g., `v0.0.2`), and publish
4. Publishing triggers the PyPI publish workflow

### TestPyPI

To publish a test release, go to Actions > "Publish to TestPyPI" > Run workflow.

### Trusted Publisher Setup (one-time)

On [pypi.org](https://pypi.org/manage/project/gemara-py/settings/publishing/)
and [test.pypi.org](https://test.pypi.org/manage/project/gemara-py/settings/publishing/),
add a trusted publisher with:

- **Owner:** `complytime`
- **Repository:** `gemara-py`
- **Workflow:** `publish-pypi.yml` (PyPI) or `publish-testpypi.yml` (TestPyPI)
- **Environment:** `pypi` or `testpypi`
