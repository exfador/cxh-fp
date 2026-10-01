RESET = "\033[0m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
MUTED = "\033[90m"
BOLD = "\033[1m"
WHITE = "\033[97m"
STATUS_COLORS = {"info": CYAN, "ok": GREEN, "warn": YELLOW, "error": RED}
STATUS_LABELS = {
    "ru": {"info": "ИНФО", "ok": "ГОТОВО", "warn": "ВНИМАНИЕ", "error": "ОШИБКА"},
    "en": {"info": "INFO", "ok": "OK", "warn": "WARNING", "error": "ERROR"},
}
ERROR_KEYS = frozenset(
    {
        "token_unauthorized",
        "token_format",
        "username_error",
        "password_mismatch",
        "secret_unavailable",
        "failed",
        "missing_environment",
        "token_response_error",
    }
)
WARNING_KEYS = frozenset({"token_timeout", "token_rate_limit", "cancelled"})
INFO_KEYS = frozenset(
    {"token_checking", "environment", "venv", "dependencies", "launch", "preview"}
)
