#!/usr/bin/env python3
"""Generate Pydantic v2 models from Gemara CUE schemas.

Usage: python3 generate.py <version>
Example: python3 generate.py v1.3.0
"""

import json
import os
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
    output_file = os.path.join(output_dir, "types.py")
    init_file = os.path.join(output_dir, "__init__.py")
    with open(init_file, "w") as f:
        f.write(f"from gemara_py.types.{module_name}.types import *  # noqa: F401, F403\n")

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
