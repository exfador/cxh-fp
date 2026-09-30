import logging.handlers
import os
import shutil
import tempfile
from contextlib import nullcontext
from pathlib import Path

from Utils.logging_support.constants import (
    LOG_DIRECTORY,
    LOG_FILENAME,
    ARCHIVE_DIRECTORY,
    LOG_FILE_MODE,
    LOG_DIRECTORY_MODE,
    LOG_MAX_BYTES,
    LOG_ARCHIVE_COUNT,
    LOG_COPY_CHUNK,
    ROTATED_PATTERN,
    ARCHIVED_PATTERN,
    LOG_FAILURE_MESSAGE,
    LOG_ROTATION_FAILURE_MESSAGE,
)


def log_path(root):
    return Path(root).resolve() / LOG_DIRECTORY / LOG_FILENAME


def ensure_log_directory(path):
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Log paths cannot be symbolic links")
    path.parent.mkdir(mode=LOG_DIRECTORY_MODE, parents=True, exist_ok=True)
    if path.exists() and not path.is_file():
        raise ValueError("Log destination must be a regular file")


class RecoveringFileHandler(logging.handlers.RotatingFileHandler):
    def __init__(self, filename, warning):
        self.warning = warning
        self.failed = False
        super().__init__(
            filename,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_ARCHIVE_COUNT,
            encoding="utf-8",
            delay=True,
        )

    def _open(self):
        path = Path(self.baseFilename)
        ensure_log_directory(path)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, LOG_FILE_MODE)
        return os.fdopen(descriptor, self.mode, encoding=self.encoding)

    def rotation_filename(self, default_name):
        index = default_name.rsplit(".", 1)[-1]
        directory = Path(self.baseFilename).parent / ARCHIVE_DIRECTORY
        if directory.is_symlink():
            raise ValueError("Log archive cannot be a symbolic link")
        directory.mkdir(mode=LOG_DIRECTORY_MODE, parents=True, exist_ok=True)
        return str(directory / f"log.{index}.log")

    def reopen_if_needed(self):
        path = Path(self.baseFilename)
        ensure_log_directory(path)
        if self.stream is None:
            return
        if not path.exists() or not os.path.samestat(
            os.fstat(self.stream.fileno()), path.stat()
        ):
            self.stream.close()
            self.stream = None

    def emit(self, record):
        try:
            self.reopen_if_needed()
            rotation_ok = self.rotate_if_needed(record)
            if self.stream is None:
                self.stream = self._open()
            self.stream.write(self.format(record) + self.terminator)
            self.flush()
            if rotation_ok:
                self.failed = False
        except Exception:
            self.report_failure()

    def rotate_if_needed(self, record):
        if not self.shouldRollover(record):
            return True
        try:
            self.doRollover()
            return True
        except (OSError, ValueError):
            self.report_failure(LOG_ROTATION_FAILURE_MESSAGE)
            return False

    def handleError(self, record):
        self.report_failure()

    def report_failure(self, message=LOG_FAILURE_MESSAGE):
        if not self.failed:
            self.warning(message)
        self.failed = True


def snapshot_logs(root, lock=None):
    path = log_path(root)
    ensure_log_directory(path)
    snapshot = tempfile.SpooledTemporaryFile(max_size=LOG_COPY_CHUNK, mode="w+b")
    try:
        with lock or nullcontext(), path.open("rb") as incoming:
            shutil.copyfileobj(incoming, snapshot, LOG_COPY_CHUNK)
        snapshot.seek(0)
        return snapshot
    except BaseException:
        snapshot.close()
        raise


def clear_log_archives(root):
    path = log_path(root)
    ensure_log_directory(path)
    candidates = list(path.parent.iterdir())
    archive = path.parent / ARCHIVE_DIRECTORY
    if archive.is_dir() and not archive.is_symlink():
        candidates.extend(archive.iterdir())
    deleted = 0
    for item in candidates:
        if item.is_symlink() or not item.is_file():
            continue
        if ROTATED_PATTERN.fullmatch(item.name) or ARCHIVED_PATTERN.fullmatch(
            item.name
        ):
            item.unlink(missing_ok=True)
            deleted += 1
    return deleted
