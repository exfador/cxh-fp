from contextlib import contextmanager
from pathlib import Path

from Utils.single_instance_guard import SingleInstanceGuard


@contextmanager
def backup_lock(root):
    path = Path(root) / "run" / "backup.lock"
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Backup lock cannot be a symbolic link")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        SingleInstanceGuard._prepare_lock_byte(handle)
        SingleInstanceGuard._lock(handle)
        try:
            yield
        finally:
            SingleInstanceGuard._unlock(handle)
