from hashlib import sha256
from pathlib import PurePosixPath

from app.constants.update_runtime import (
    UPDATE_DEPENDENCY_FILES,
    UPDATE_DEPENDENCY_ROOT,
    UPDATE_REQUIRED_ENTRY,
)


def verify_runtime_dependencies(root, files):
    if UPDATE_REQUIRED_ENTRY not in files:
        raise ValueError("Release entry point missing")
    incoming = {name: digest for name, digest in files.items() if is_dependency(name)}
    existing = {
        str(path.relative_to(root).as_posix()): path
        for path in (root / UPDATE_DEPENDENCY_ROOT).rglob("*")
        if path.is_file()
    }
    existing.update(
        {
            name: root / name
            for name in UPDATE_DEPENDENCY_FILES
            if (root / name).is_file()
        }
    )
    if set(incoming) != set(existing):
        raise ValueError("Dependency changes require setup.py before installation")
    for name, path in existing.items():
        if path.is_symlink() or sha256(path.read_bytes()).hexdigest() != incoming[name]:
            raise ValueError("Dependency changes require setup.py before installation")


def is_dependency(name):
    return (
        name in UPDATE_DEPENDENCY_FILES
        or PurePosixPath(name).parts[0] == UPDATE_DEPENDENCY_ROOT
    )
