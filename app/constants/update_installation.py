UPDATE_DIRECTORY = "storage/updates"
TRANSACTION_DIRECTORY = "transactions"
PENDING_FILENAME = "pending.json"
LOCK_FILENAME = "install.lock"
STAGE_DIRECTORY = "stage"
ORIGINAL_DIRECTORY = "originals"
PREVIOUS_DIRECTORY = "previous"
PREVIOUS_JOURNAL = "manifest.json"
RETENTION_STAGE_PREFIX = "retention-"
PREVIOUS_RELEASE_COUNT = 2
MUTABLE_PROFILE_ROOT = "bot-profile"
PYTHON_SOURCE_SUFFIX = ".py"
PYTHON_CACHE_OPTIMIZATIONS = ("", "1", "2")
INSTALLATION_LOGGER = "CoxerHubBot.updates.installer"
TRANSACTION_CLEANUP_ERROR = "Update journal cleared; temporary cleanup failed (%s)"
JOURNAL_VERSION = 1
PHASE_INSTALLED = "installed"
PHASE_APPLYING = "applying"
PHASE_BOOTING = "booting"
PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
FILE_MODE_MASK = 0o777
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_EXTRACTED_BYTES = 256 * 1024 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_FILE_COUNT = 5000
MAX_JOURNAL_BYTES = 2 * 1024 * 1024
MAX_PATH_DEPTH = 20
MAX_COMPONENT_BYTES = 240
MAX_COMPRESSION_RATIO = 500
READ_CHUNK_BYTES = 1024 * 1024
TRANSACTION_TOKEN_BYTES = 16
SHA256_PATTERN = "[0-9a-f]{64}"
TRANSACTION_PATTERN = "[0-9a-f]{32}"
JOURNAL_FIELDS = frozenset(
    {"version", "phase", "transaction", "files", "originals", "created_directories"}
)
CODE_ROOTS = frozenset(
    {
        "app",
        "FunPayAPI",
        "Utils",
        "cardinal_core",
        "bot_handlers",
        "plugin_services",
        "tg_bot",
        "locales",
        "requirements",
        "tools",
        "assets",
        "bot-profile",
        "docs",
        ".github",
    }
)
ENTRY_FILES = frozenset(
    {
        "main.py",
        "cardinal.py",
        "setup.py",
        "first_setup.py",
        "handlers.py",
        "start.py",
        "Setup.bat",
        "Start.bat",
        "start.sh",
        "start.bat",
        "install.sh",
        "requirements.txt",
        "requirements-dev.txt",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "pyproject.toml",
        "docker-compose.yml",
        "Dockerfile",
        "coxerhub-bot@.service",
        ".gitignore",
        ".dockerignore",
        "NOTICE",
        "NOTICE.md",
        "CoxerHub.ico",
    }
)
FORBIDDEN_COMPONENTS = frozenset(
    {
        "configs",
        "storage",
        "plugins",
        "logs",
        "run",
        "private",
        ".git",
        ".env",
        ".venv",
        "venv",
        "__pycache__",
    }
)
FORBIDDEN_SUFFIXES = frozenset(
    {".pyc", ".pyo", ".pem", ".key", ".sqlite", ".sqlite3", ".db", ".log"}
)
WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }
)
FORBIDDEN_PATH_CHARACTERS = frozenset('<>:"\\|?*')
MIN_PRINTABLE_CHARACTER = 32
ZIP_ENCRYPTION_FLAG = 1
WINDOWS_PLATFORM = "nt"
