import os
import shutil
import tempfile
from pathlib import Path

from Utils.backups.constants import PRIVATE_FILE_MODE


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(source, temporary)
        os.chmod(temporary, PRIVATE_FILE_MODE)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def save_originals(root, files, rollback):
    saved = {}
    for _, destination in files:
        if destination.exists() and not destination.is_file():
            raise ValueError("Restore target is not a regular file")
        original = rollback / destination.relative_to(root)
        saved[destination] = original if destination.exists() else None
        if destination.exists():
            atomic_copy(destination, original)
    return saved


def undo_changes(applied, originals):
    for destination in reversed(applied):
        original = originals[destination]
        if original is None:
            destination.unlink(missing_ok=True)
        else:
            atomic_copy(original, destination)


def restore_files(root, files):
    directory = root / "run"
    directory.mkdir(parents=True, exist_ok=True)
    rollback = Path(tempfile.mkdtemp(prefix="restore-", dir=directory))
    applied = []
    try:
        originals = save_originals(root, files, rollback)
        for source, destination in files:
            applied.append(destination)
            atomic_copy(source, destination)
    except BaseException:
        try:
            undo_changes(applied, originals if applied else {})
        except OSError as error:
            raise RuntimeError(
                f"Restore rollback failed; originals retained in {rollback}"
            ) from error
        shutil.rmtree(rollback)
        raise
    shutil.rmtree(rollback)
