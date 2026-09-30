import copy
import logging
import json
import shutil
import textwrap

from app.setup.terminal import supports_color
from Utils.logging_support.constants import (
    COLOR_PATTERN,
    MARKER_PATTERN,
    TOKEN_PATTERN,
    SECRET_PATTERN,
    MULTIVALUE_SECRET_PATTERN,
    PAYLOAD_KEY_PATTERN,
    PAYLOAD_START_PATTERN,
    PROXY_PATTERN,
    REDACTED,
    CONSOLE_MAX_WIDTH,
    CONSOLE_MIN_WIDTH,
    CONSOLE_DATE_FORMAT,
    FILE_FORMAT,
    FILE_DATE_FORMAT,
    LEVEL_COLORS,
    COLOR_RESET,
    DETAILS_MESSAGE,
)


def clean_text(value):
    text = COLOR_PATTERN.sub("", str(value))
    text = MARKER_PATTERN.sub("", text)
    text = TOKEN_PATTERN.sub(REDACTED, text)
    text = MULTIVALUE_SECRET_PATTERN.sub(lambda match: match[1] + REDACTED, text)
    text = SECRET_PATTERN.sub(lambda match: match[1] + REDACTED, text)
    return PROXY_PATTERN.sub(lambda match: match[1] + "://" + REDACTED + "@", text)


def safe_message(record):
    try:
        return clean_text(record.getMessage())
    except (TypeError, ValueError):
        return clean_text(record.msg)


def has_payload(message):
    if PAYLOAD_KEY_PATTERN.search(message):
        return True
    decoder = json.JSONDecoder()
    for match in PAYLOAD_START_PATTERN.finditer(message):
        try:
            value, _ = decoder.raw_decode(message, match.start())
        except (ValueError, RecursionError):
            continue
        if isinstance(value, (list, dict)):
            return True
    return False


class ConsoleFilter(logging.Filter):
    def filter(self, record):
        if record.levelno < logging.INFO:
            return False
        message = safe_message(record)
        return bool(message.strip()) and (
            record.levelno >= logging.WARNING or not has_payload(message)
        )


class CLILoggerFormatter(logging.Formatter):
    def __init__(self, color=None):
        super().__init__()
        self.color = supports_color() if color is None else color

    def format(self, record):
        message = safe_message(record)
        if has_payload(message):
            message = DETAILS_MESSAGE
        message = " ".join(message.split())
        width = max(
            CONSOLE_MIN_WIDTH,
            min(shutil.get_terminal_size().columns, CONSOLE_MAX_WIDTH),
        )
        message = textwrap.shorten(message, width=width, placeholder=" …")
        level = record.levelname.replace("WARNING", "WARN")
        text = f"{self.formatTime(record, CONSOLE_DATE_FORMAT)}  {level:<5}  {message}"
        color = LEVEL_COLORS.get(record.levelname, "") if self.color else ""
        return f"{color}{text}{COLOR_RESET if color else ''}"


class FileLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(FILE_FORMAT, FILE_DATE_FORMAT)

    def format(self, record):
        cloned = copy.copy(record)
        cloned.msg, cloned.args = safe_message(record), ()
        cloned.exc_text = None
        return clean_text(super().format(cloned))
