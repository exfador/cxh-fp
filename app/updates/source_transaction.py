import shutil
import logging
from pathlib import Path

from app.constants import update_installation as settings
from app.updates.install_state import (
    atomic_write,
    digest_bytes,
    file_bytes,
    safe_path,
    sync_directory,
    transaction_path,
)
from app.updates.bytecode import purge_source_bytecode


def snapshot_sources(root, transaction, files):
    originals = {}
    total = 0
    for name in files:
        destination = safe_path(root, name)
        if not destination.exists():
            continue
        data = file_bytes(destination)
        total += len(data)
        if total > settings.MAX_EXTRACTED_BYTES:
            raise ValueError("Original source snapshot exceeds the limit")
        atomic_write(
            safe_path(transaction / settings.ORIGINAL_DIRECTORY, name),
            data,
            destination.stat().st_mode & settings.FILE_MODE_MASK,
        )
        originals[name] = digest_bytes(data)
    return originals


def missing_directories(root, files):
    missing = set()
    for name in files:
        for directory in Path(name).parents:
            if directory == Path("."):
                continue
            if not safe_path(root, directory).exists():
                missing.add(directory.as_posix())
    return sorted(missing, key=lambda name: len(Path(name).parts), reverse=True)


def apply_sources(root, transaction, files):
    for name, digest in files.items():
        source = safe_path(transaction / settings.STAGE_DIRECTORY, name)
        data = file_bytes(source)
        if digest_bytes(data) != digest:
            raise ValueError("Staged update was modified")
        destination = safe_path(root, name)
        if preserve_existing_profile(destination, name):
            continue
        purge_source_bytecode(root, name)
        mode = (
            destination.stat().st_mode & settings.FILE_MODE_MASK
            if destination.exists()
            else settings.PRIVATE_FILE_MODE
        )
        atomic_write(destination, data, mode)


def validate_originals(root, transaction, state):
    originals = {}
    total = 0
    for name, digest in state["originals"].items():
        source = safe_path(transaction / settings.ORIGINAL_DIRECTORY, name)
        data = file_bytes(source)
        total += len(data)
        if total > settings.MAX_EXTRACTED_BYTES:
            raise ValueError("Original source snapshot exceeds the limit")
        if digest_bytes(data) != digest:
            raise ValueError("Original update snapshot was modified")
        originals[name] = (data, source.stat().st_mode & settings.FILE_MODE_MASK)
    for name in state["files"]:
        destination = safe_path(root, name)
        if destination.exists() and not destination.is_file():
            raise ValueError("Update rollback target is not a regular file")
    return originals


def rollback_sources(root, directory, state):
    transaction = transaction_path(directory, state["transaction"])
    originals = validate_originals(root, transaction, state)
    for name in state["files"]:
        destination = safe_path(root, name)
        if name in originals and preserve_existing_profile(destination, name):
            continue
        purge_source_bytecode(root, name)
        if name in originals:
            data, mode = originals[name]
            atomic_write(destination, data, mode)
        else:
            destination.unlink(missing_ok=True)
            if destination.parent.exists():
                sync_directory(destination.parent)
    remove_created_directories(root, state["created_directories"])
    cleanup_transaction(directory, state)


def preserve_existing_profile(destination, name):
    return Path(name).parts[0] == settings.MUTABLE_PROFILE_ROOT and destination.exists()


def remove_created_directories(root, names):
    for name in sorted(names, key=lambda value: len(Path(value).parts), reverse=True):
        directory = safe_path(root, name)
        if directory.exists() and not any(directory.iterdir()):
            directory.rmdir()
            sync_directory(directory.parent)


def cleanup_transaction(directory, state):
    pending = safe_path(directory, settings.PENDING_FILENAME)
    pending.unlink(missing_ok=True)
    try:
        sync_directory(directory)
        transaction = transaction_path(directory, state["transaction"])
        if transaction.exists():
            shutil.rmtree(transaction)
    except OSError as error:
        logging.getLogger(settings.INSTALLATION_LOGGER).warning(
            settings.TRANSACTION_CLEANUP_ERROR, type(error).__name__
        )
