"""Read capability metadata without importing or executing numerical tools."""

from pathlib import Path

import yaml

CAPABILITIES_ROOT = Path(__file__).resolve().parent


def _load_yaml(relative_path: str) -> dict:
    with (CAPABILITIES_ROOT / relative_path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def load_catalog() -> dict:
    return _load_yaml("catalog.yaml")


def list_tool_bundles() -> list[str]:
    return list(load_catalog()["tool_bundles"])


def get_tool_manifest(bundle_name: str) -> dict:
    return _load_yaml(load_catalog()["tool_bundles"][bundle_name])


def list_robot_families() -> list[str]:
    return list(load_catalog()["robot_families"])


def get_robot_family_grammar(family_name: str) -> dict:
    return _load_yaml(load_catalog()["robot_families"][family_name])
