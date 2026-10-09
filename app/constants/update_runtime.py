from pathlib import Path

UPDATE_REPOSITORY = "exfador/cxh-fp"
UPDATE_PUBLIC_KEY = "dda382fc2feabdd8198fd1dac0b3395b12198a44c19f39df96af183f0fe791a7"
UPDATE_RELEASE_API = "https://api.github.com/repos/{}/releases/latest"
UPDATE_MANIFEST_ASSET = "cxh-fp-manifest.json"
UPDATE_ARCHIVE_ASSET = "cxh-fp.zip"
UPDATE_STATE_PATH = Path("storage/updates/notifications.json")
UPDATE_REQUEST_PATH = Path("storage/updates/request.json")
UPDATE_INITIAL_SECONDS = 30
UPDATE_POLL_SECONDS = 21600
UPDATE_STATE_LIMIT = 512 * 1024
UPDATE_TOKEN_BYTES = 16
UPDATE_CALLBACK_PREFIX = "cxh_update"
UPDATE_THREAD_NAME = "cxh-signed-updates"
UPDATE_CHECK_COOLDOWN = 30
UPDATE_LOGGER = "CoxerHubBot.updates"
UPDATE_CONTENT_FIELDS = frozenset(
    {"repository", "version", "files", "archive_sha256", "archive_size"}
)
UPDATE_DEPENDENCY_ROOT = "requirements"
UPDATE_DEPENDENCY_FILES = frozenset({"requirements.txt", "requirements-dev.txt"})
UPDATE_REQUIRED_ENTRY = "main.py"
UPDATE_CHILD_FLAG = "CXH_UPDATE_CHILD"
UPDATE_HEALTH_NONCE = "CXH_UPDATE_HEALTH_NONCE"
UPDATE_HEALTH_PATH = Path("storage/updates/healthy.json")
UPDATE_EXIT_CODE = 75
UPDATE_RESTART_EXIT_CODE = 76
UPDATE_CTRL_C_EXIT_CODE = 0xC000013A
UPDATE_BOOT_TIMEOUT = 180
UPDATE_STOP_TIMEOUT = 15
UPDATE_TICK_SECONDS = 1
UPDATE_RESTART_INITIAL_SECONDS = 5
UPDATE_RESTART_MAX_SECONDS = 60
UPDATE_RESTART_STABLE_SECONDS = 300
UPDATE_CHILD_VALUE = "1"
UPDATE_AUTH_PATH = Path("storage/cache/tg_authorized_users.json")
UPDATE_SUPERVISOR_LOCK = Path("run/update-supervisor.lock")
UPDATE_SIGNED_FIELDS = frozenset(
    {"envelope", "recipient", "message_id", "previous_version"}
)
