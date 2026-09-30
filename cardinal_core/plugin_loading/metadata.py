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
    uuid = result.get("UUID")
    if not isinstance(uuid, str) or str(UUID(uuid, version=4)) != uuid:
        raise ValueError("Plugin must declare a static UUID v4")
    return result
