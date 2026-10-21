from hashlib import sha256
from pathlib import Path

from app.updates.dependencies import verify_runtime_dependencies


def preview_release(root, manifest):
    root = Path(root)
    added, changed = [], []
    for name, expected in manifest["files"].items():
        path = root / name
        if not path.is_file():
            added.append(name)
        elif path.is_symlink() or sha256(path.read_bytes()).hexdigest() != expected:
            changed.append(name)
    compatible = True
    try:
        verify_runtime_dependencies(root, manifest["files"])
    except ValueError:
        compatible = False
    return {
        "added": len(added),
        "changed": len(changed),
        "compatible": compatible,
        "areas": sorted({name.split("/")[0] for name in added + changed})[:12],
    }
