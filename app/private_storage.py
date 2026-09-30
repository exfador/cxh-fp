import os
from pathlib import Path

from app.constants.filesystem import (
    PRIVATE_DIRECTORY_MODE,
    PRIVATE_FILE_MODE,
    PRIVATE_STORAGE_DIRECTORIES,
    PRIVATE_STORAGE_FILES,
    PRIVATE_STORAGE_SYMLINK_ERROR,
)


def restrict_private_path(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(PRIVATE_STORAGE_SYMLINK_ERROR)
    if path.exists():
        mode = PRIVATE_DIRECTORY_MODE if path.is_dir() else PRIVATE_FILE_MODE
        path.chmod(mode)


def restrict_private_tree(directory):
    restrict_private_path(directory)
    if not directory.exists():
        return
    for current, directories, filenames in os.walk(directory, followlinks=False):
        for name in (*directories, *filenames):
            restrict_private_path(Path(current) / name)


def secure_existing_storage(root):
    root = Path(root)
    for name in PRIVATE_STORAGE_DIRECTORIES:
        restrict_private_tree(root / name)
    for name in PRIVATE_STORAGE_FILES:
        restrict_private_path(root / name)
