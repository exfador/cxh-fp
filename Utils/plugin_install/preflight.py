import ast
import platform
import re
import sys
import tempfile
from pathlib import Path

from Utils.plugin_install.archive import extract_archive
from Utils.plugin_install.service import (
    checked_entry,
    package_directory,
    validate_filename,
)
from Utils.plugin_install.constants import MAX_UPLOAD_BYTES


def inspect_package(data, filename, existing=()):
    filename = validate_filename(filename)
    if not isinstance(data, bytes) or not data or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Invalid package size")
    with tempfile.TemporaryDirectory(prefix="cxh-package-check-") as temporary:
        root = Path(temporary)
        if filename.endswith(".zip"):
            extract_archive(data, root)
        else:
            (root / filename).write_bytes(data)
        root = package_directory(root)
        entry = checked_entry(root)
        tree = ast.parse((root / entry).read_bytes())
        metadata, warnings = {}, []
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id in {"NAME", "VERSION", "UUID"}
                        and isinstance(node.value.value, str)
                    ):
                        metadata[target.id] = node.value.value[:160]
        if metadata.get("UUID") in existing:
            warnings.append("UUID already loaded / UUID уже загружен")
        imports = [
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ]
        names = [p.name for p in root.rglob("*") if p.is_file()]
        binary = [n for n in names if n.endswith((".so", ".pyd"))]
        if (
            binary
            and platform.system() == "Windows"
            and not any(n.endswith(".pyd") for n in binary)
        ):
            warnings.append("Linux runtime only / Только рантайм Linux")
        if (
            binary
            and platform.system() == "Linux"
            and not any(n.endswith(".so") for n in binary)
        ):
            warnings.append("Windows runtime only / Только рантайм Windows")
        tags = {
            m[1] for n in binary if (m := re.search(r"(?:cp|cpython-)(\d{2,3})", n))
        }
        current = f"{sys.version_info.major}{sys.version_info.minor}"
        if tags and current not in tags:
            warnings.append("Python ABI differs / Версия Python рантайма отличается")
        for module in imports:
            if module.startswith("plugins."):
                part = module.split(".")[1]
                if not (root / part).exists() and not (root / (part + ".py")).exists():
                    warnings.append(
                        "Check dependency / Проверьте зависимость: " + part[:80]
                    )
        return {
            "entry": entry,
            "metadata": metadata,
            "warnings": warnings[:8],
            "files": len(names),
        }
