MANIFEST_FIELDS = frozenset(
    {"version", "archive_sha256", "archive_size", "files", "repository"}
)
ENVELOPE_FIELDS = frozenset({"manifest", "signature"})
MAX_MANIFEST_BYTES = 256 * 1024
MAX_RELEASE_JSON_BYTES = 1024 * 1024
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_MANIFEST_FILES = 2000
MAX_FILE_PATH_BYTES = 240
MAX_REPOSITORY_LENGTH = 140
MAX_VERSION_COMPONENT = 999999
VERSION_COMPONENTS = 3
PUBLIC_KEY_BYTES = 32
SIGNATURE_BYTES = 64
DIGEST_HEX_LENGTH = 64
HEX_CHARACTERS = frozenset("0123456789abcdef")
PORTABLE_FORBIDDEN_CHARACTERS = frozenset('\\<>:"|?*')
WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)
TRUSTED_RELEASE_HOSTS = frozenset(
    {
        "api.github.com",
        "github.com",
        "release-assets.githubusercontent.com",
        "objects.githubusercontent.com",
    }
)
INITIAL_RELEASE_HOSTS = frozenset({"api.github.com", "github.com"})
MAX_REDIRECTS = 4
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
SUCCESS_STATUS = 200
HTTPS_PORT = 443
REQUEST_TIMEOUT = (5, 30)
CHUNK_BYTES = 64 * 1024
PRIVATE_DOWNLOAD_MODE = 0o600
RELEASE_REQUEST_HEADERS = {
    "Accept": "application/octet-stream",
    "User-Agent": "CXH-FP-Release-Client",
    "Accept-Encoding": "identity",
}
MANIFEST_ERROR = "Invalid signed update manifest"
SIGNATURE_ERROR = "Update signature verification failed"
CRYPTOGRAPHY_REQUIRED = "Ed25519 verification requires the cryptography dependency"
DOWNGRADE_ERROR = "Update version must be newer than the installed version"
TRANSPORT_ERROR = "Invalid GitHub release transport"
DOWNLOAD_SIZE_ERROR = "Update download size does not match its signed manifest"
DOWNLOAD_DIGEST_ERROR = "Update download SHA-256 does not match its signed manifest"
REPOSITORY_ERROR = "Update repository does not match the configured repository"
PRIVATE_MANIFEST_ROOTS = frozenset(
    {"configs", "storage", "logs", "plugins", ".git", ".env", "__pycache__", ".venv"}
)
MAX_RELEASE_URL_LENGTH = 8192
MAX_LENGTH_HEADER_DIGITS = 20
MAX_VERSION_TEXT_LENGTH = 20

RELEASE_JSON_REQUEST_HEADERS = {**RELEASE_REQUEST_HEADERS, "Accept": "application/json"}
DOCKER_RUNTIME_MARKER = "/.dockerenv"
MANAGED_RUNTIME_ERROR = "Managed updates require a supervised source installation"
UPDATE_RESULT_STATUSES = frozenset({"done", "rollback"})
UPDATE_RESULT_FIELDS = frozenset(
    {"envelope", "recipient", "message_id", "previous_version", "status", "version"}
)
