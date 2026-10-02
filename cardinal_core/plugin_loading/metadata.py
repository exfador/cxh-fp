import ast
from pathlib import Path
from uuid import UUID

from cardinal_core.plugin_loading.constants import MAX_PLUGIN_BYTES


def read_static_metadata(path: Path) -> dict:
    if path.stat().st_size > MAX_PLUGIN_BYTES:
        raise ValueError("Plugin source is too large")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            try:
                result[target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
    if "UUID" in result:
        validate_uuid(result["UUID"])
    return result


def validate_uuid(value: object) -> None:
    try:
        valid = isinstance(value, str) and str(UUID(value, version=4)) == value
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Plugin UUID must be a canonical UUID v4 string")
