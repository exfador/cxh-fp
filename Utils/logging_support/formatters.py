import copy
import logging
import json
import shutil
import textwrap
import re

from urllib3.exceptions import ReadTimeoutError, ConnectTimeoutError

from app.terminal_colors import supports_color
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
    CONSOLE_TIME_COLOR,
    CONSOLE_SOURCE_COLOR,
    CONSOLE_TEXT_COLOR,
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


def network_retry_message(record):
    if (
        record.name != "urllib3.connectionpool"
        or not str(record.msg).startswith("Retrying (")
        or not isinstance(record.args, tuple)
        or len(record.args) != 3
    ):
        return None
    error = record.args[1]
    host = getattr(getattr(error, "pool", None), "host", None)
    host = (
        host
        if isinstance(host, str) and re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host)
        else "сервер"
    )
    if isinstance(error, ReadTimeoutError):
        reason = "не ответил за отведённое время"
    elif isinstance(error, ConnectTimeoutError):
        reason = "недоступен: не удалось установить соединение"
    else:
        reason = "соединение прервано"
    return f"{host}: {reason}. Повторяю запрос. Подробности: logs/log.log"


class ConsoleFilter(logging.Filter):
    def filter(self, record):
        if record.levelno < logging.INFO:
            return False
        message = safe_message(record)
        return bool(message.strip()) and (
            record.levelno >= logging.WARNING or not has_payload(message)
        )


class CLILoggerFormatter(logging.Formatter):
    def __init__(self, color=None, stream=None):
        super().__init__()
        self.color = supports_color(stream) if color is None else color

    def format(self, record):
        message = network_retry_message(record) or safe_message(record)
        if has_payload(message):
            message = DETAILS_MESSAGE
        message = " ".join(message.split())
        width = max(
            CONSOLE_MIN_WIDTH,
            min(shutil.get_terminal_size().columns, CONSOLE_MAX_WIDTH),
        )
        level = record.levelname.replace("WARNING", "WARN")
        timestamp = self.formatTime(record, CONSOLE_DATE_FORMAT)
        source = self.source(record.name)
        prefix = f"  {timestamp}  {level:<8}  {source:<8} │ "
        lines = textwrap.wrap(message, width=max(12, width - len(prefix))) or [""]
        header = (
            "  "
            + self.paint(timestamp, CONSOLE_TIME_COLOR)
            + "  "
            + self.paint(f"{level:<8}", LEVEL_COLORS.get(record.levelname, ""))
            + "  "
            + self.paint(f"{source:<8}", CONSOLE_SOURCE_COLOR)
            + self.paint(" │ ", CONSOLE_TIME_COLOR)
        )
        body_color = (
            LEVEL_COLORS.get(record.levelname, CONSOLE_TEXT_COLOR)
            if record.levelno >= logging.WARNING
            else CONSOLE_TEXT_COLOR
        )
        continuation = " " * (len(prefix) - 2) + self.paint("│ ", CONSOLE_TIME_COLOR)
        return "\n".join(
            (header if index == 0 else continuation) + self.paint(line, body_color)
            for index, line in enumerate(lines)
        )

    def paint(self, text, color):
        return f"{color}{text}{COLOR_RESET}" if self.color and color else text

    @staticmethod
    def source(name):
        normalized = name.casefold()
        if "telegram" in normalized or "tgbot" in normalized or "telebot" in normalized:
            return "TELEGRAM"
        if "plugin" in normalized or normalized.startswith("fpc."):
            return "PLUGIN"
        if "funpay" in normalized or "runner" in normalized:
            return "FUNPAY"
        if "update" in normalized:
            return "UPDATE"
        if normalized.startswith("urllib3"):
            return "NETWORK"
        return "SYSTEM"


class FileLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(FILE_FORMAT, FILE_DATE_FORMAT)

    def format(self, record):
        cloned = copy.copy(record)
        cloned.msg, cloned.args = safe_message(record), ()
        cloned.exc_text = None
        return clean_text(super().format(cloned))
