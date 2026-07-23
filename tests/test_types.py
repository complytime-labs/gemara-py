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

    roundtrip = obj.model_dump(by_alias=True, mode='json')
    assert roundtrip["metadata"]["id"] == data["metadata"]["id"]
    assert roundtrip["metadata"]["type"] == data["metadata"]["type"]


@pytest.mark.parametrize("version,module_name", VERSIONS)
def test_metadata_fields(version, module_name):
    fixture_path = CUE_CACHE / f"gemara@{version}" / "test" / "test-data" / "good-ccc.yaml"
    if not fixture_path.exists():
        pytest.skip(f"Fixture good-ccc.yaml not available for {version}")

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
