import os
import tempfile
import unicodedata
from pathlib import Path, PurePosixPath

from tg_bot.constants.file_upload import (
    EMPTY_FILENAMES,
    FORBIDDEN_FILENAME_CHARACTERS,
    MAX_FILENAME_BYTES,
    MAX_UPLOAD_BYTES,
    MIN_PRINTABLE_CHARACTER,
    PRIVATE_FILE_MODE,
)
from Utils.backups.archive import checked_destination, validate_portable_path


def upload_destination(directory, filename):
    if not isinstance(filename, str) or filename in EMPTY_FILENAMES:
        raise ValueError("Invalid upload filename")
    if filename != unicodedata.normalize("NFC", filename):
        raise ValueError("Upload filename must be normalized")
    if len(filename.encode("utf-8")) > MAX_FILENAME_BYTES:
        raise ValueError("Upload filename exceeds the limit")
    if any(
        char in FORBIDDEN_FILENAME_CHARACTERS or ord(char) < MIN_PRINTABLE_CHARACTER
        for char in filename
    ):
        raise ValueError("Unsafe upload filename")
    validate_portable_path(PurePosixPath(filename))
    directory = Path(directory).absolute()
    return checked_destination(directory, Path(filename))


def store_upload(directory, filename, data):
    destination = upload_destination(directory, filename)
    if not isinstance(data, bytes) or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file exceeds the limit")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        temporary.chmod(PRIVATE_FILE_MODE)
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        upload_destination(directory, filename)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
