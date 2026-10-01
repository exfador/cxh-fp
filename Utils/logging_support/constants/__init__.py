from pathlib import Path
import re

LOG_DIRECTORY = Path("logs")
LOG_FILENAME = "log.log"
ARCHIVE_DIRECTORY = "archive"
LOG_MAX_BYTES = 20 * 1024 * 1024
LOG_ARCHIVE_COUNT = 10
LOG_FILE_MODE = 0o600
LOG_DIRECTORY_MODE = 0o700
LOG_QUEUE_SIZE = 8192
LOG_COPY_CHUNK = 1024 * 1024
CONSOLE_MAX_WIDTH = 180
CONSOLE_MIN_WIDTH = 60
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
CONSOLE_DATE_FORMAT = "%H:%M:%S"
LOGGER_NAMES = (
    "main",
    "FunPayAPI",
    "FunPay CoxerHub",
    "CoxerHubBot",
    "TGBot",
    "TeleBot",
    "urllib3",
    "urllib3.connectionpool",
    "httpx",
    "httpcore",
)
PAYLOAD_LOGGER_NAMES = frozenset(
    {"TeleBot", "urllib3", "urllib3.connectionpool", "httpx", "httpcore"}
)
COLOR_PATTERN = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07)")
MARKER_PATTERN = re.compile(
    r"\$(?:B_)?(?:YELLOW|CYAN|MAGENTA|BLUE|GREEN|BLACK|WHITE|RESET)"
)
TOKEN_PATTERN = re.compile(r"\d{5,20}:[A-Za-z0-9_-]{30,80}")
SECRET_PATTERN = re.compile(
    r"""(?i)(["']?(?:golden_key|token|password|passwd|secretKeyHash|secret|seed|seed_phrase|authorization|cookie|set-cookie)["']?\s*[:=]\s*)("[^"\r\n]*"|'[^'\r\n]*'|[^\s,;\r\n]+)"""
)
MULTIVALUE_SECRET_PATTERN = re.compile(
    r"""(?i)(["']?(?:seed_phrase|seed|authorization|cookie|set-cookie)["']?\s*[:=]\s*)("[^"\r\n]*"|'[^'\r\n]*'|[^\r\n]+)"""
)
PAYLOAD_KEY_PATTERN = re.compile(r"[\"']\s*:")
PAYLOAD_START_PATTERN = re.compile(r"[\[{]")
PROXY_PATTERN = re.compile(r"(https?|socks[45]h?)://[^\s/@]+:[^\s/@]+@", re.I)
ROTATED_PATTERN = re.compile(r"log\.log\.?\d+\Z")
ARCHIVED_PATTERN = re.compile(r"log\.\d+\.log\Z")
LEVEL_COLORS = {
    "DEBUG": "\033[90m",
    "INFO": "\033[96m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[1;91m",
}
CONSOLE_TIME_COLOR = "\033[90m"
CONSOLE_SOURCE_COLOR = "\033[94m"
CONSOLE_TEXT_COLOR = "\033[97m"
COLOR_RESET = "\033[0m"
DETAILS_MESSAGE = "Diagnostic payload saved to logs/log.log"
LOG_FAILURE_MESSAGE = (
    "Log file unavailable; check logs folder permissions and free disk space."
)
LOG_ROTATION_FAILURE_MESSAGE = (
    "Log rotation unavailable; entries continue in logs/log.log."
)
QUEUE_OVERFLOW_MESSAGE = "Logging queue is full; some diagnostic events were skipped."
REDACTED = "[REDACTED]"
