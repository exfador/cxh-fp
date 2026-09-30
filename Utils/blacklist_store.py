import json
import os
import tempfile
from pathlib import Path

from Utils.constants.blacklist import (
    BLACKLIST_JSON_INDENT,
    BLACKLIST_PATH,
    BLACKLIST_TEMP_PREFIX,
)


def write_blacklist(names):
    if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
        raise ValueError("Blacklist must contain strings")
    destination = BLACKLIST_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise OSError("Blacklist path cannot be a symbolic link")
    descriptor, temporary = tempfile.mkstemp(
        prefix=BLACKLIST_TEMP_PREFIX, dir=destination.parent
    )
    try:
        write_blacklist_file(descriptor, names)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_blacklist_file(descriptor, names):
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(names, stream, indent=BLACKLIST_JSON_INDENT)
        stream.flush()
        os.fsync(stream.fileno())
