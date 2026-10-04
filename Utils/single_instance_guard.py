import errno
import os
from pathlib import Path
from typing import BinaryIO


class SingleInstanceGuard:
    _lock_handle: BinaryIO | None = None

    @classmethod
    def acquire(cls, lock_path: Path) -> None:
        if cls._lock_handle is not None:
            return
        resolved_path = lock_path.resolve()
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        lock_handle = resolved_path.open("a+b")
        cls._prepare_lock_byte(lock_handle)
        try:
            cls._lock(lock_handle)
        except OSError as error:
            lock_handle.close()
            if error.errno not in {errno.EACCES, errno.EAGAIN}:
                raise
            raise SystemExit(
                "FPC уже запущен из этой папки. Используйте работающего бота или "
                "остановите его перед повторным запуском. / FPC is already running."
            ) from None
        cls._lock_handle = lock_handle

    @classmethod
    def release(cls) -> None:
        lock_handle = cls._lock_handle
        if lock_handle is None:
            return
        cls._unlock(lock_handle)
        lock_handle.close()
        cls._lock_handle = None

    @staticmethod
    def _prepare_lock_byte(lock_handle: BinaryIO) -> None:
        lock_handle.seek(0, os.SEEK_END)
        if lock_handle.tell() == 0:
            lock_handle.write(b"\x00")
            lock_handle.flush()
        lock_handle.seek(0)

    @staticmethod
    def _lock(lock_handle: BinaryIO) -> None:
        if os.name == "nt":
            import msvcrt

            windows_locking = vars(msvcrt)["locking"]
            windows_locking(lock_handle.fileno(), vars(msvcrt)["LK_NBLCK"], 1)
            return
        import fcntl

        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(lock_handle: BinaryIO) -> None:
        lock_handle.seek(0)
        if os.name == "nt":
            import msvcrt

            windows_locking = vars(msvcrt)["locking"]
            windows_locking(lock_handle.fileno(), vars(msvcrt)["LK_UNLCK"], 1)
            return
        import fcntl

        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
