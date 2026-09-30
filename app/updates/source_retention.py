import os
import json
import re
import shutil
import tempfile
from pathlib import Path

from app.constants import update_installation as settings
from app.updates.install_state import (
    atomic_write,
    ensure_directory,
    safe_path,
    sync_directory,
    transaction_path,
    write_pending,
)
from app.updates.source_transaction import validate_originals


def retain_previous(root, directory, state):
    previous = safe_path(directory, settings.PREVIOUS_DIRECTORY)
    ensure_directory(previous)
    previous.chmod(settings.PRIVATE_DIRECTORY_MODE)
    target = safe_path(previous, state["transaction"])
    if target.exists():
        validate_previous(root, target, state)
        prune_previous(previous)
        return
    transaction = transaction_path(directory, state["transaction"])
    originals = validate_originals(root, transaction, state)
    temporary = Path(
        tempfile.mkdtemp(prefix=settings.RETENTION_STAGE_PREFIX, dir=previous)
    )
    try:
        write_originals(temporary, originals)
        write_pending(temporary, state)
        os.replace(
            temporary / settings.PENDING_FILENAME, temporary / settings.PREVIOUS_JOURNAL
        )
        sync_directory(temporary)
        os.replace(temporary, target)
        sync_directory(previous)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    prune_previous(previous)


def validate_previous(root, directory, state):
    path = safe_path(directory, settings.PREVIOUS_JOURNAL)
    if path.stat().st_size > settings.MAX_JOURNAL_BYTES:
        raise ValueError("Previous journal exceeds the limit")
    if json.loads(path.read_text(encoding="utf-8")) != state:
        raise ValueError("Previous source snapshot journal differs")
    validate_originals(root, directory, state)


def write_originals(directory, originals):
    for name, (data, mode) in originals.items():
        destination = safe_path(directory, Path(settings.ORIGINAL_DIRECTORY) / name)
        atomic_write(destination, data, mode)


def prune_previous(directory):
    snapshots = []
    for entry in directory.iterdir():
        if re.fullmatch(settings.TRANSACTION_PATTERN, entry.name):
            checked = safe_path(directory, entry.name)
            if not checked.is_dir():
                raise ValueError("Previous snapshot is not a directory")
            snapshots.append(checked)
    snapshots.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for path in snapshots[settings.PREVIOUS_RELEASE_COUNT :]:
        shutil.rmtree(path)
    sync_directory(directory)
