import json
import os
import tempfile
from pathlib import Path

from app.constants.update_runtime import UPDATE_STATE_LIMIT
from app.updates.manifest import reject_duplicate_fields


def checked_state_path(path):
    path = Path(path)
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Update state cannot traverse symbolic links")
    return path


def load_state(path):
    path = checked_state_path(path)
    if not path.exists():
        return {}
    if path.stat().st_size > UPDATE_STATE_LIMIT:
        raise ValueError("Update state is too large")
    payload = path.read_bytes()
    if len(payload) > UPDATE_STATE_LIMIT:
        raise ValueError("Update state is too large")
    result = json.loads(
        payload.decode("utf-8"), object_pairs_hook=reject_duplicate_fields
    )
    if not isinstance(result, dict):
        raise ValueError("Invalid update state")
    return result


def write_state(path, data):
    path = checked_state_path(path)
    payload = json.dumps(
        data, ensure_ascii=True, sort_keys=True, allow_nan=False
    ).encode("utf-8")
    if not isinstance(data, dict) or len(payload) > UPDATE_STATE_LIMIT:
        raise ValueError("Update state is too large or invalid")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, name = tempfile.mkstemp(dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
