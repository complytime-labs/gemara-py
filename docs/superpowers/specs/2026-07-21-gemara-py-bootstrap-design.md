# gemara-py Bootstrap Design

## Overview

gemara-py is a Python package that provides versioned Pydantic v2 models generated
from Gemara CUE schemas. It follows the same pattern as
[go-oscal](https://github.com/defenseunicorns/go-oscal): one directory per spec
version, generated types checked into the repo.

## Package Structure

```
gemara-py/
  gemara_py/
    __init__.py                  # re-exports latest version types
    types/
      __init__.py
      gemara_1_0_0/__init__.py   # generated Pydantic v2 models for v1.0.0
      gemara_1_2_0/__init__.py   # generated Pydantic v2 models for v1.2.0
      gemara_1_3_0/__init__.py   # generated Pydantic v2 models for v1.3.0
  tests/
    test_types.py                # round-trip validation tests
  generate.py                    # CUE -> JSON Schema -> Pydantic pipeline
  Makefile                       # generate, test, lint targets
  pyproject.toml                 # package metadata
  README.md
  LICENSE                        # Apache 2.0
```

## Spec Versions

Initial generation covers stable releases only:
- v1.0.0
- v1.2.0
- v1.3.0

Pre-v1 and release candidates are excluded. New versions are added by appending
to the `SPECVERSIONS` list in the Makefile and re-running `make generate`.

## Generation Pipeline

`generate.py` drives the full pipeline for a single spec version, invoked as:

```
python3 generate.py <version>
# e.g. python3 generate.py v1.3.0
```

### Steps

1. **Discover definitions** -- run `cue eval github.com/gemaraproj/gemara@<version>`
   and parse output lines starting with `#` to extract all definition names
   (e.g. `#ControlCatalog`, `#Actor`, `#Metadata`). Skip internal definitions
   starting with `#_`.

2. **Export each definition** -- for each definition, run
   `cue def -e '#Foo' --out jsonschema github.com/gemaraproj/gemara@<version>`
   to get a JSON Schema with `$defs` for transitive dependencies.

3. **Merge and fix** -- combine all per-definition JSON Schemas into one:
   - Collect all `$defs` entries from every export into a single `$defs` map.
   - Add each root definition to `$defs` under its clean name.
   - Strip `#` prefix from `$defs` keys.
   - Replace `%23` (URL-encoded `#`) in all `$ref` paths.
   - Flatten struct embedding: CUE uses `$ref` alongside `properties` for struct
     embedding. Inline the referenced definition's properties into the referencing
     definition and remove the `$ref`.
   - Inline dot-qualified `$defs`: CUE may emit path-qualified names like
     `ControlEvaluation.control."reference-id"` which cause `datamodel-codegen`
     to create subdirectories. Replace `$ref`s to these with inline schemas.
   - Fix metadata narrowing: CUE narrows per-artifact `metadata` to only the
     overridden `type` field. Replace these partial inline schemas with a `$ref`
     to the full `Metadata` definition.
   - Write the merged schema to a temporary file.

4. **Generate Pydantic models** -- run `datamodel-codegen` on the merged schema:
   ```
   datamodel-codegen \
     --input <merged_schema.json> \
     --input-file-type jsonschema \
     --output gemara_py/types/gemara_X_Y_Z/__init__.py \
     --output-model-type pydantic_v2.BaseModel \
     --target-python-version 3.11
   ```

5. **Clean up** -- remove the temporary merged schema file.

### Error handling

If `cue def` fails for a specific definition (e.g. an internal/unexported type),
log a warning and skip it. If `datamodel-codegen` fails, exit with an error.

## Makefile

```makefile
SPECVERSIONS := v1.0.0 v1.2.0 v1.3.0

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

## Dependencies

### Runtime (required to use the package)

- `pydantic >= 2.0`

### Development / generation (not needed by end users)

- `cue` CLI (v0.17+)
- `datamodel-code-generator`
- `pytest` (for tests)
- `pyyaml` (for loading test fixtures)
- `ruff` (for linting/formatting)

Generated types are checked into the repo, so consumers install the package
and get Pydantic models with no code generation step.

## pyproject.toml

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
```

## Usage

```python
# Use latest version (v1.3.0)
from gemara_py import ControlCatalog, EvaluationLog

# Pin to a specific version
from gemara_py.types.gemara_1_3_0 import ControlCatalog
from gemara_py.types.gemara_1_0_0 import ControlCatalog as ControlCatalogV1
```

## Top-Level Re-export

`gemara_py/__init__.py` re-exports all public types from the latest version
module (`gemara_1_3_0`). When a new spec version is added, this import is
updated to point to the new latest.

## Tests

`tests/test_types.py` validates that generated models work correctly:

1. **Fixture loading** -- load YAML test fixtures from the Gemara CUE package's
   `test/` directory (cached in `~/.cache/cue/mod/extract/`).
2. **Parse and validate** -- deserialize YAML into the corresponding Pydantic
   model and assert no validation errors.
3. **Round-trip** -- serialize back to dict and compare key fields against
   the original fixture.
4. **Version coverage** -- run the above for each generated version.

## Adding a New Version

1. Add the version tag to `SPECVERSIONS` in the Makefile.
2. Run `make generate`.
3. Update `gemara_py/__init__.py` to re-export from the new latest version.
4. Add test fixtures if available.
5. Commit the generated files and open a PR.
