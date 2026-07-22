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
pip install -e ".[dev]"
task generate
```

## Development

```bash
pip install -e ".[dev]"
task test
task lint
```
