import re
import time
from threading import Lock

from telebot.apihelper import ApiTelegramException

from tg_bot.constants.chat_sync import (
    CHAT_SYNC_ECHO_SECONDS,
    CHAT_SYNC_THREAD_CLOSED,
    CHAT_SYNC_THREAD_MISSING,
)


def retry_after(error):
    if not isinstance(error, ApiTelegramException) or error.error_code != 429:
        return None
    parameters = (getattr(error, "result_json", None) or {}).get("parameters") or {}
    try:
        return max(1.0, float(parameters.get("retry_after", 5)))
    except (TypeError, ValueError):
        return 5.0


def error_matches(error, markers):
    if not isinstance(error, ApiTelegramException):
        return False
    description = str(getattr(error, "description", "") or error).casefold()
    return any(marker in description for marker in markers)


def thread_missing(error):
    return error_matches(error, CHAT_SYNC_THREAD_MISSING)


def thread_closed(error):
    return error_matches(error, CHAT_SYNC_THREAD_CLOSED)


def text_signature(text):
    return re.sub(r"\s+", " ", text or "").strip()


class EchoFilter:
    IMAGE = "\0image"

    def __init__(self, ttl=CHAT_SYNC_ECHO_SECONDS, clock=time.monotonic):
        self.ttl = ttl
        self.clock = clock
        self.lock = Lock()
        self.ids = {}
        self.pending = []

    def prune(self):
        now = self.clock()
        self.ids = {key: until for key, until in self.ids.items() if until > now}
        self.pending = [item for item in self.pending if item[2] > now]

    def expect(self, chat_id, text=None):
        signature = text_signature(text) if text else self.IMAGE
        with self.lock:
            self.prune()
            self.pending.append((str(chat_id), signature, self.clock() + self.ttl))

    def sent(self, chat_id, messages):
        with self.lock:
            for message in messages or ():
                if getattr(message, "id", None):
                    self.ids[(str(chat_id), message.id)] = self.clock() + self.ttl

    def drop_pending(self, chat_id, signature):
        for index, item in enumerate(self.pending):
            if item[0] == chat_id and item[1] == signature:
                del self.pending[index]
                return True
        return False

    def consume(self, message):
        chat_id = str(message.chat_id)
        signature = text_signature(message.text) if message.text else self.IMAGE
        with self.lock:
            self.prune()
            if self.ids.pop((chat_id, message.id), None) is not None:
                self.drop_pending(chat_id, signature)
                return True
            return self.drop_pending(chat_id, signature)
