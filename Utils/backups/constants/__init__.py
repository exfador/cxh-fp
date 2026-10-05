from pathlib import Path

BACKUP_ROOTS = frozenset({"storage", "configs", "plugins"})
BACKUP_PATH = Path("backup.zip")
UPLOAD_PATH = Path("storage/cache/backup.zip")
STAGING_PATH = Path("storage/cache/backup")
MAX_ARCHIVE_FILES = 10_000
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
EXCLUDED_DIRECTORIES = frozenset({"__pycache__"})
EXCLUDED_SUFFIXES = frozenset({".lock"})

ZIP_ENCRYPTION_FLAG = 1
PRIVATE_FILE_MODE = 0o600

EXCLUDED_PATHS = frozenset({UPLOAD_PATH, STAGING_PATH})
BACKUP_PREVIOUS_PATH = Path("backup.previous.zip")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024

WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)
WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"\\|?*')
MIN_PRINTABLE_CHARACTER = 32
