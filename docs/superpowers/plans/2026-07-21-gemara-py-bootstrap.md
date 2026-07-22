# gemara-py Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap a Python package that generates versioned Pydantic v2 models from Gemara CUE schemas, following the go-oscal pattern.

**Architecture:** A `generate.py` script exports each CUE definition to JSON Schema via `cue def`, merges them into one schema with fixups for CUE-specific patterns ($ref encoding, struct embedding, metadata narrowing, dot-qualified paths), then runs `datamodel-codegen` to produce Pydantic v2 models. Generated types are checked into versioned subdirectories under `gemara_py/types/`.

**Tech Stack:** Python 3.11+, Pydantic v2, datamodel-code-generator, CUE CLI v0.17+, pytest, PyYAML, ruff

## Global Constraints

- Python >= 3.11
- Pydantic >= 2.0
- Flat package layout (no `src/` directory)
- Generated types are checked into the repo
- Spec versions: v1.0.0, v1.2.0, v1.3.0
- CUE package: `github.com/gemaraproj/gemara`
- All commits signed: `git commit -S -s`
- Run `gitleaks detect --config ~/.gitleaks.toml --source . -v` before every commit
- No secrets, API keys, tokens, or private catalog content

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, dependencies, build config |
| `Makefile` | `generate`, `test`, `lint`, `format` targets |
| `gemara_py/__init__.py` | Re-exports all public types from latest version (v1.3.0) |
| `gemara_py/types/__init__.py` | Empty package marker |
| `gemara_py/types/gemara_1_0_0/__init__.py` | Generated Pydantic models for Gemara v1.0.0 |
| `gemara_py/types/gemara_1_2_0/__init__.py` | Generated Pydantic models for Gemara v1.2.0 |
| `gemara_py/types/gemara_1_3_0/__init__.py` | Generated Pydantic models for Gemara v1.3.0 |
| `generate.py` | CUE -> JSON Schema -> Pydantic pipeline |
| `tests/test_types.py` | Round-trip validation tests against CUE test fixtures |

---

### Task 1: Project scaffolding and pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `gemara_py/__init__.py`
- Create: `gemara_py/types/__init__.py`

**Interfaces:**
- Consumes: nothing
- Produces: installable Python package structure; `make generate`, `make test`, `make lint`, `make format` targets

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "gemara-py"
version = "0.1.0"
description = "Gemara types as Pydantic models"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.11"
dependencies = ["pydantic>=2.0"]

[project.optional-dependencies]
dev = [
    "datamodel-code-generator",
    "pytest",
    "pyyaml",
    "ruff",
]

[tool.setuptools.packages.find]
include = ["gemara_py*"]

[tool.ruff]
target-version = "py311"
line-length = 120
```

- [ ] **Step 2: Create `Makefile`**

```makefile
SPECVERSIONS := v1.0.0 v1.2.0 v1.3.0

.PHONY: generate test lint format

generate:
	@for v in $(SPECVERSIONS); do \
		echo "Generating types for $$v..."; \
		python3 generate.py $$v || exit 1; \
	done

test:
	python3 -m pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .
```

- [ ] **Step 3: Create package `__init__.py` files**

Create `gemara_py/__init__.py` as a placeholder (will be populated in Task 4):

```python
"""Gemara types as Pydantic models."""
```

Create `gemara_py/types/__init__.py` as an empty file.

- [ ] **Step 4: Verify the package installs**

Run: `pip install -e ".[dev]" 2>&1 | tail -5`
Expected: successful installation

- [ ] **Step 5: Commit**

```bash
gitleaks detect --config ~/.gitleaks.toml --source . -v
git add pyproject.toml Makefile gemara_py/__init__.py gemara_py/types/__init__.py
git commit -S -s -m "feat: add project scaffolding with pyproject.toml and Makefile"
```

---

### Task 2: Generation script

**Files:**
- Create: `generate.py`

**Interfaces:**
- Consumes: CUE CLI (`cue def`, `cue eval`), `datamodel-codegen` CLI
- Produces: `generate(version: str) -> None` — writes Pydantic models to `gemara_py/types/gemara_X_Y_Z/__init__.py`

- [ ] **Step 1: Create `generate.py`**

```python
#!/usr/bin/env python3
"""Generate Pydantic v2 models from Gemara CUE schemas.

Usage: python3 generate.py <version>
Example: python3 generate.py v1.3.0
"""

import json
import os
import re
import subprocess
import sys
import tempfile


CUE_PACKAGE = "github.com/gemaraproj/gemara"


def discover_definitions(version: str) -> list[str]:
    result = subprocess.run(
        ["cue", "eval", f"{CUE_PACKAGE}@{version}"],
        capture_output=True,
        text=True,
        check=True,
    )
    defnames = set()
    for line in result.stdout.splitlines():
        if line.startswith("#") and not line.startswith("#_"):
            name = line.split(":")[0].split(" ")[0].strip()
            defnames.add(name)
    return sorted(defnames)


def export_definition(defname: str, version: str) -> dict | None:
    result = subprocess.run(
        ["cue", "def", "-e", defname, "--out", "jsonschema", f"{CUE_PACKAGE}@{version}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  WARN: skipping {defname}: {result.stderr.strip()}", file=sys.stderr)
        return None
    raw = result.stdout.replace("%23", "")
    return json.loads(raw)


def merge_schemas(definitions: list[str], version: str) -> dict:
    merged = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {}}
    for defname in definitions:
        schema = export_definition(defname, version)
        if schema is None:
            continue
        for k, v in schema.get("$defs", {}).items():
            merged["$defs"][k.lstrip("#")] = v
        root = {k: v for k, v in schema.items() if k not in ("$schema", "$defs")}
        merged["$defs"][defname.lstrip("#")] = root
    return merged


def flatten_struct_embedding(merged: dict) -> None:
    def resolve_ref(ref: str) -> dict | None:
        parts = ref.lstrip("#/").split("/")
        if len(parts) == 2 and parts[0] == "$defs":
            return merged["$defs"].get(parts[1])
        return None

    changed = True
    while changed:
        changed = False
        for defn in list(merged["$defs"].values()):
            if "$ref" in defn and ("properties" in defn or "type" in defn):
                ref_target = resolve_ref(defn["$ref"])
                if ref_target is None:
                    continue
                if "properties" not in defn:
                    defn["properties"] = {}
                for pk, pv in ref_target.get("properties", {}).items():
                    if pk not in defn["properties"]:
                        defn["properties"][pk] = pv
                existing_required = defn.get("required", [])
                for req in ref_target.get("required", []):
                    if req not in existing_required:
                        existing_required.append(req)
                if existing_required:
                    defn["required"] = existing_required
                if "additionalProperties" in ref_target and "additionalProperties" not in defn:
                    defn["additionalProperties"] = ref_target["additionalProperties"]
                del defn["$ref"]
                changed = True


def inline_dot_qualified_defs(merged: dict) -> None:
    dot_defs = {k: v for k, v in merged["$defs"].items() if "." in k}
    for dot_name, dot_val in dot_defs.items():
        raw = json.dumps(merged)
        ref_pattern = f"#/$defs/{dot_name}"
        encoded_name = dot_name.replace('"', "%22")
        encoded_ref = f"#/$defs/{encoded_name}"
        raw = raw.replace(json.dumps({"$ref": ref_pattern}), json.dumps(dot_val))
        raw = raw.replace(json.dumps({"$ref": encoded_ref}), json.dumps(dot_val))
        merged.clear()
        merged.update(json.loads(raw))
        merged["$defs"].pop(dot_name, None)


def fix_metadata_narrowing(merged: dict) -> None:
    for defn in merged["$defs"].values():
        if "properties" not in defn:
            continue
        for prop_name, prop_schema in defn["properties"].items():
            if (
                prop_name == "metadata"
                and isinstance(prop_schema, dict)
                and prop_schema.get("type") == "object"
                and "properties" in prop_schema
                and set(prop_schema["properties"].keys()) == {"type"}
                and "$ref" not in prop_schema
            ):
                defn["properties"][prop_name] = {"$ref": "#/$defs/Metadata"}


def version_to_module_name(version: str) -> str:
    return "gemara_" + version.lstrip("v").replace(".", "_")


def generate(version: str) -> None:
    print(f"Generating Pydantic models for Gemara {version}")

    print("  Discovering definitions...")
    definitions = discover_definitions(version)
    print(f"  Found {len(definitions)} definitions")

    print("  Exporting and merging JSON Schemas...")
    merged = merge_schemas(definitions, version)

    print("  Flattening struct embedding...")
    flatten_struct_embedding(merged)

    print("  Inlining dot-qualified definitions...")
    inline_dot_qualified_defs(merged)

    print("  Fixing metadata narrowing...")
    fix_metadata_narrowing(merged)

    module_name = version_to_module_name(version)
    output_dir = os.path.join("gemara_py", "types", module_name)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "__init__.py")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(merged, f, indent=2)
        schema_path = f.name

    try:
        print(f"  Running datamodel-codegen -> {output_file}")
        subprocess.run(
            [
                "datamodel-codegen",
                "--input", schema_path,
                "--input-file-type", "jsonschema",
                "--output", output_file,
                "--output-model-type", "pydantic_v2.BaseModel",
                "--target-python-version", "3.11",
            ],
            check=True,
        )
    finally:
        os.unlink(schema_path)

    print(f"  Done: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <version>", file=sys.stderr)
        print(f"Example: {sys.argv[0]} v1.3.0", file=sys.stderr)
        sys.exit(1)
    generate(sys.argv[1])
```

- [ ] **Step 2: Test generation for v1.3.0**

Run: `python3 generate.py v1.3.0`
Expected: output like:
```
Generating Pydantic models for Gemara v1.3.0
  Discovering definitions...
  Found 89 definitions
  Exporting and merging JSON Schemas...
  Flattening struct embedding...
  Inlining dot-qualified definitions...
  Fixing metadata narrowing...
  Running datamodel-codegen -> gemara_py/types/gemara_1_3_0/__init__.py
  Done: gemara_py/types/gemara_1_3_0/__init__.py
```

Verify: `python3 -c "from gemara_py.types.gemara_1_3_0 import ControlCatalog; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Test generation for all versions**

Run: `make generate`
Expected: generates types for v1.0.0, v1.2.0, and v1.3.0 without errors.

Verify all three modules import:
```bash
python3 -c "from gemara_py.types.gemara_1_0_0 import ControlCatalog; print('v1.0.0 OK')"
python3 -c "from gemara_py.types.gemara_1_2_0 import ControlCatalog; print('v1.2.0 OK')"
python3 -c "from gemara_py.types.gemara_1_3_0 import ControlCatalog; print('v1.3.0 OK')"
```

- [ ] **Step 4: Commit**

```bash
gitleaks detect --config ~/.gitleaks.toml --source . -v
git add generate.py gemara_py/types/
git commit -S -s -m "feat: add generation script and generated Pydantic types for v1.0.0, v1.2.0, v1.3.0"
```

---

### Task 3: Top-level re-exports and tests

**Files:**
- Modify: `gemara_py/__init__.py`
- Create: `tests/test_types.py`

**Interfaces:**
- Consumes: generated type modules under `gemara_py/types/gemara_X_Y_Z/`
- Produces: `from gemara_py import ControlCatalog` convenience import; pytest test suite

- [ ] **Step 1: Write the test file**

The test fixtures live in the CUE module cache. Each test loads a YAML fixture,
parses it into the corresponding Pydantic model, and verifies key fields.
The `model_rebuild()` call with `_types_namespace` is needed because the generated
code uses `from __future__ import annotations`.

Create `tests/test_types.py`:

```python
import os
from pathlib import Path

import pytest
import yaml

CUE_CACHE = Path.home() / ".cache" / "cue" / "mod" / "extract" / "github.com" / "gemaraproj"

FIXTURE_MAP = {
    "ControlCatalog": "good-ccc.yaml",
    "GuidanceCatalog": "good-aigf.yaml",
    "Policy": "good-policy.yaml",
    "EnforcementLog": "good-enforcement-log.yaml",
    "AuditLog": "good-audit-log.yaml",
    "MappingDocument": "good-mapping-document.yaml",
    "RiskCatalog": "good-risk-catalog.yaml",
    "ThreatCatalog": "good-threat-catalog.yaml",
    "VectorCatalog": "good-aigf-vectors.yaml",
    "PrincipleCatalog": "good-aigf-principles.yaml",
    "Lexicon": "good-lexicon.yaml",
    "CapabilityCatalog": "good-capability-catalog.yaml",
}

VERSIONS = [
    ("v1.0.0", "gemara_1_0_0"),
    ("v1.2.0", "gemara_1_2_0"),
    ("v1.3.0", "gemara_1_3_0"),
]


def _rebuild_models(mod):
    from pydantic import BaseModel, RootModel

    ns = {name: getattr(mod, name) for name in dir(mod)}
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and issubclass(obj, (BaseModel, RootModel)) and obj not in (BaseModel, RootModel):
            try:
                obj.model_rebuild(_types_namespace=ns)
            except Exception:
                pass


def _load_fixture(version: str, filename: str) -> dict:
    fixture_path = CUE_CACHE / f"gemara@{version}" / "test" / "test-data" / filename
    with open(fixture_path) as f:
        return yaml.safe_load(f)


def _get_version_module(module_name: str):
    import importlib

    return importlib.import_module(f"gemara_py.types.{module_name}")


@pytest.mark.parametrize("version,module_name", VERSIONS)
@pytest.mark.parametrize("type_name,fixture_file", FIXTURE_MAP.items())
def test_fixture_round_trip(version, module_name, type_name, fixture_file):
    fixture_path = CUE_CACHE / f"gemara@{version}" / "test" / "test-data" / fixture_file
    if not fixture_path.exists():
        pytest.skip(f"Fixture {fixture_file} not available for {version}")

    mod = _get_version_module(module_name)
    _rebuild_models(mod)

    cls = getattr(mod, type_name, None)
    if cls is None:
        pytest.skip(f"{type_name} not in {module_name}")

    data = _load_fixture(version, fixture_file)
    obj = cls.model_validate(data)

    assert obj.metadata.id is not None
    assert obj.metadata.description is not None

    roundtrip = obj.model_dump(by_alias=True)
    assert roundtrip["metadata"]["id"] == data["metadata"]["id"]
    assert roundtrip["metadata"]["type"] == data["metadata"]["type"]


@pytest.mark.parametrize("version,module_name", VERSIONS)
def test_metadata_fields(version, module_name):
    mod = _get_version_module(module_name)
    _rebuild_models(mod)

    data = _load_fixture(version, "good-ccc.yaml")
    catalog = mod.ControlCatalog.model_validate(data)

    assert catalog.metadata.id == "FINOS-CCC"
    assert catalog.metadata.author.name == "FINOS"
    assert catalog.metadata.gemara_version is not None


def test_top_level_reexport():
    from gemara_py import ControlCatalog

    assert ControlCatalog is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_types.py -v --tb=short 2>&1 | tail -20`
Expected: `test_top_level_reexport` FAILS because `gemara_py/__init__.py` doesn't re-export yet. The fixture tests should PASS.

- [ ] **Step 3: Update `gemara_py/__init__.py` with re-exports**

```python
"""Gemara types as Pydantic models."""

from gemara_py.types.gemara_1_3_0 import *  # noqa: F401, F403
```

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest tests/test_types.py -v`
Expected: all tests PASS

- [ ] **Step 5: Run lint**

Run: `ruff check .`
Expected: no errors (or only the expected F401/F403 suppression in `__init__.py`)

- [ ] **Step 6: Commit**

```bash
gitleaks detect --config ~/.gitleaks.toml --source . -v
git add gemara_py/__init__.py tests/test_types.py
git commit -S -s -m "feat: add top-level re-exports and fixture round-trip tests"
```

---

### Task 4: README and cleanup

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: all prior tasks
- Produces: user-facing documentation

- [ ] **Step 1: Update README.md**

```markdown
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

Requires [CUE](https://cuelang.org/) v0.17+ and development dependencies:

```bash
pip install -e ".[dev]"
make generate
```

## Development

```bash
pip install -e ".[dev]"
make test
make lint
```
```

- [ ] **Step 2: Final verification**

Run: `make test`
Expected: all tests pass

Run: `make lint`
Expected: clean

Run: `python3 -c "from gemara_py import ControlCatalog; print(ControlCatalog.__name__)"`
Expected: `ControlCatalog`

- [ ] **Step 3: Commit**

```bash
gitleaks detect --config ~/.gitleaks.toml --source . -v
git add README.md
git commit -S -s -m "docs: add README with usage and development instructions"
```
