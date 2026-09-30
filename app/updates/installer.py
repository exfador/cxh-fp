import shutil
from pathlib import Path

from app.constants import update_installation as settings
from app.updates.install_archive import extract_release, validate_files
from app.updates.install_state import (
    create_transaction,
    installation_lock,
    load_pending,
    write_pending,
)
from app.updates.source_transaction import (
    apply_sources,
    cleanup_transaction,
    missing_directories,
    rollback_sources,
    snapshot_sources,
)
from app.updates.source_retention import retain_previous


def install_archive(root, archive_path, files):
    root = Path(root).absolute()
    files = validate_files(files)
    with installation_lock(root) as directory:
        if load_pending(directory) is not None:
            raise ValueError("An update is awaiting startup validation")
        token, transaction = create_transaction(directory)
        try:
            extract_release(
                Path(archive_path), transaction / settings.STAGE_DIRECTORY, files
            )
            state = prepare_transaction(root, transaction, token, files)
            write_pending(directory, state)
            apply_sources(root, transaction, files)
            state["phase"] = settings.PHASE_INSTALLED
            write_pending(directory, state)
        except BaseException:
            pending = load_pending(directory)
            if pending is not None:
                rollback_sources(root, directory, pending)
            else:
                shutil.rmtree(transaction)
            raise
        return transaction


def prepare_transaction(root, transaction, token, files):
    return {
        "version": settings.JOURNAL_VERSION,
        "phase": settings.PHASE_APPLYING,
        "transaction": token,
        "files": files,
        "originals": snapshot_sources(root, transaction, files),
        "created_directories": missing_directories(root, files),
    }


def rollback_pending(root):
    root = Path(root).absolute()
    with installation_lock(root) as directory:
        state = load_pending(directory)
        if state is None:
            return False
        rollback_sources(root, directory, state)
        return True


def commit_pending(root):
    with installation_lock(root) as directory:
        state = load_pending(directory)
        if state is None:
            return False
        if state["phase"] != settings.PHASE_BOOTING:
            raise ValueError("Update cannot commit before startup validation")
        retain_previous(Path(root).absolute(), directory, state)
        cleanup_transaction(directory, state)
        return True


def mark_boot_pending(root):
    root = Path(root).absolute()
    with installation_lock(root) as directory:
        state = load_pending(directory)
        if state is None:
            return False
        if state["phase"] in {settings.PHASE_BOOTING, settings.PHASE_APPLYING}:
            rollback_sources(root, directory, state)
            return False
        state["phase"] = settings.PHASE_BOOTING
        write_pending(directory, state)
        return True
