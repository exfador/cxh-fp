import logging
import re
from pathlib import Path

from colorama import Back, Fore, Style

from app.constants.runtime import PROJECT_ROOT
from Utils.logging_support.formatters import CLILoggerFormatter, FileLoggerFormatter
from Utils.logging_support.runtime import LoggingRuntime, current_runtime

__all__ = (
    "configure_logging",
    "CLILoggerFormatter",
    "FileLoggerFormatter",
    "LOG_COLORS",
    "CLI_LOG_FORMAT",
    "CLI_TIME_FORMAT",
    "FILE_LOG_FORMAT",
    "FILE_TIME_FORMAT",
    "CLEAR_RE",
    "LOGGER_NAMES",
    "add_colors",
)

LOG_COLORS = {
    logging.DEBUG: Fore.BLACK + Style.BRIGHT,
    logging.INFO: Fore.GREEN,
    logging.WARN: Fore.YELLOW,
    logging.ERROR: Fore.RED,
    logging.CRITICAL: Back.RED,
}
CLI_LOG_FORMAT = (
    f"{Fore.BLACK + Style.BRIGHT}[%(asctime)s]{Style.RESET_ALL}"
    f"{Fore.CYAN}>{Style.RESET_ALL} $RESET%(levelname).1s: %(message)s{Style.RESET_ALL}"
)
CLI_TIME_FORMAT = "%d-%m-%Y %H:%M:%S"
FILE_LOG_FORMAT = (
    "[%(asctime)s][%(filename)s][%(lineno)d]> %(levelname).1s: %(message)s"
)
FILE_TIME_FORMAT = "%d.%m.%y %H:%M:%S"
CLEAR_RE = re.compile(r"(\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]))|(\n)|(\r)")
LOGGER_NAMES = ["main", "FunPayAPI", "FPC", "TGBot", "FunPay CoxerHub", "CoxerHubBot"]
COLOR_MARKERS = {
    "$YELLOW": Fore.YELLOW,
    "$CYAN": Fore.CYAN,
    "$MAGENTA": Fore.MAGENTA,
    "$BLUE": Fore.BLUE,
    "$GREEN": Fore.GREEN,
    "$BLACK": Fore.BLACK,
    "$WHITE": Fore.WHITE,
    "$B_YELLOW": Back.YELLOW,
    "$B_CYAN": Back.CYAN,
    "$B_MAGENTA": Back.MAGENTA,
    "$B_BLUE": Back.BLUE,
    "$B_GREEN": Back.GREEN,
    "$B_BLACK": Back.BLACK,
    "$B_WHITE": Back.WHITE,
}


def add_colors(text: str) -> str:
    for marker, color in COLOR_MARKERS.items():
        text = text.replace(marker, color)
    return text


def configure_logging(root=PROJECT_ROOT, stream=None):
    existing = current_runtime()
    if existing is not None:
        existing.stop()
    return LoggingRuntime(Path(root), stream).start()


def flush_logs():
    runtime = current_runtime()
    if runtime is not None:
        runtime.flush()


def stop_logging():
    runtime = current_runtime()
    if runtime is not None:
        runtime.stop()
