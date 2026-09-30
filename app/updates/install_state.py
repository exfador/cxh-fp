import hashlib
import json
import os
import re
import secrets
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from app.constants import update_installation as settings
from app.updates.install_archive import release_path, validate_files

if os.name == settings.WINDOWS_PLATFORM:
    import msvcrt
else:
    import fcntl


def safe_path(root, relative):
    root = Path(root).absolute()
    destination = root / relative
    if not destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("Update path escapes its root")
    for part in (destination, *destination.parents):
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError("Update path contains a symbolic link")
    return destination


def update_directory(root):
    directory = safe_path(root, settings.UPDATE_DIRECTORY)
    directory.mkdir(mode=settings.PRIVATE_DIRECTORY_MODE, parents=True, exist_ok=True)
    directory.chmod(settings.PRIVATE_DIRECTORY_MODE)
    return directory


def sync_directory(directory):
    if os.name == settings.WINDOWS_PLATFORM:
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write(destination, data, mode=settings.PRIVATE_FILE_MODE):
    ensure_directory(destination.parent)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            if hasattr(os, "fchmod"):
                os.fchmod(handle.fileno(), mode)
            else:
                temporary.chmod(mode)
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        sync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_directory(directory):
    missing = []
    for parent in (directory, *directory.parents):
        if parent.exists():
            break
        missing.append(parent)
    for parent in reversed(missing):
        parent.mkdir(mode=settings.PRIVATE_DIRECTORY_MODE)
        sync_directory(parent.parent)


def file_bytes(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Update source is not a regular file")
    with path.open("rb") as handle:
        data = handle.read(settings.MAX_FILE_BYTES + 1)
    if len(data) > settings.MAX_FILE_BYTES:
        raise ValueError("Update source exceeds the limit")
    return data


def write_pending(directory, state):
    data = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    if len(data) > settings.MAX_JOURNAL_BYTES:
        raise ValueError("Update journal exceeds the limit")
    atomic_write(safe_path(directory, settings.PENDING_FILENAME), data)


def load_pending(directory):
    path = safe_path(directory, settings.PENDING_FILENAME)
    if not path.exists():
        return None
    if path.stat().st_size > settings.MAX_JOURNAL_BYTES:
        raise ValueError("Update journal exceeds the limit")
    state = json.loads(path.read_text(encoding="utf-8"))
    validate_pending(state)
    return state


def validate_pending(state):
    if not isinstance(state, dict) or set(state) != settings.JOURNAL_FIELDS:
        raise ValueError("Invalid update journal")
    validate_pending_identity(state)
    validate_files(state["files"])
    validate_pending_originals(state)
    validate_pending_directories(state)


def validate_pending_identity(state):
    if (
        type(state["version"]) is not int
        or state["version"] != settings.JOURNAL_VERSION
        or not isinstance(state["phase"], str)
        or state["phase"]
        not in {
            settings.PHASE_INSTALLED,
            settings.PHASE_BOOTING,
            settings.PHASE_APPLYING,
        }
    ):
        raise ValueError("Unsupported update journal")
    if not isinstance(state["transaction"], str) or not re.fullmatch(
        settings.TRANSACTION_PATTERN, state["transaction"]
    ):
        raise ValueError("Invalid update transaction")


def validate_pending_originals(state):
    originals = state["originals"]
    if not isinstance(originals, dict) or not set(originals).issubset(state["files"]):
        raise ValueError("Invalid original file journal")
    if any(
        not isinstance(digest, str) or not re.fullmatch(settings.SHA256_PATTERN, digest)
        for digest in originals.values()
    ):
        raise ValueError("Invalid original file digest")


def validate_pending_directories(state):
    directories = state["created_directories"]
    if (
        not isinstance(directories, list)
        or len(directories) > settings.MAX_FILE_COUNT * settings.MAX_PATH_DEPTH
    ):
        raise ValueError("Invalid created directory journal")
    allowed_directories = {
        parent.as_posix()
        for name in state["files"]
        for parent in PurePosixPath(name).parents
    }
    for name in directories:
        release_path(name, directory=True)
        if name not in allowed_directories:
            raise ValueError("Unrelated created directory")


def transaction_path(directory, token):
    return safe_path(directory, Path(settings.TRANSACTION_DIRECTORY) / token)


def create_transaction(directory):
    token = secrets.token_hex(settings.TRANSACTION_TOKEN_BYTES)
    destination = transaction_path(directory, token)
    ensure_directory(destination.parent)
    destination.mkdir(mode=settings.PRIVATE_DIRECTORY_MODE)
    sync_directory(destination.parent)
    for name in (settings.STAGE_DIRECTORY, settings.ORIGINAL_DIRECTORY):
        (destination / name).mkdir(mode=settings.PRIVATE_DIRECTORY_MODE)
    return token, destination


@contextmanager
def installation_lock(root):
    directory = update_directory(root)
    lock = safe_path(directory, settings.LOCK_FILENAME)
    descriptor = os.open(lock, os.O_RDWR | os.O_CREAT, settings.PRIVATE_FILE_MODE)
    try:
        lock_descriptor(descriptor)
        yield directory
    finally:
        os.close(descriptor)


def lock_descriptor(descriptor):
    if os.name == settings.WINDOWS_PLATFORM:
        if not os.fstat(descriptor).st_size:
            os.write(descriptor, b"0")
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        return
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()
