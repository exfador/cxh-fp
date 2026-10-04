import json
import logging
import os
from pathlib import Path
from threading import RLock

from tg_bot.constants.order_reminder import (
    REMINDER_AUTHOR_ME,
    REMINDER_AUTHOR_OTHER,
    REMINDER_DEFAULT_HOURS,
    REMINDER_KEEP_SECONDS,
    REMINDER_LOGGER,
    REMINDER_MAX_HOURS,
    REMINDER_MIN_HOURS,
    REMINDER_PATH,
    REMINDER_TEXT_LIMIT,
)

logger = logging.getLogger(REMINDER_LOGGER)


def valid_hours(value):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and REMINDER_MIN_HOURS <= value <= REMINDER_MAX_HOURS
    )


def chat_entry(value):
    if not isinstance(value, dict):
        return None
    author, moment = value.get("author"), value.get("time")
    if author not in (REMINDER_AUTHOR_ME, REMINDER_AUTHOR_OTHER):
        return None
    if not isinstance(moment, (int, float)) or isinstance(moment, bool):
        return None
    chat_id = value.get("chat_id")
    if not isinstance(chat_id, (int, str)) or isinstance(chat_id, bool):
        chat_id = None
    return {"chat_id": chat_id, "author": author, "time": float(moment)}


class ReminderStore:
    def __init__(self, path=REMINDER_PATH):
        self.path = Path(path)
        self.lock = RLock()
        self.enabled = False
        self.hours = REMINDER_DEFAULT_HOURS
        self.text = ""
        self.reminded = {}
        self.chats = {}
        self.dirty = False
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        self.enabled = data.get("enabled") is True
        if valid_hours(data.get("hours")):
            self.hours = data["hours"]
        text = data.get("text")
        self.text = text[:REMINDER_TEXT_LIMIT] if isinstance(text, str) else ""
        self.reminded = {
            str(key): float(value)
            for key, value in (data.get("reminded") or {}).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        chats = {}
        for key, value in (data.get("chats") or {}).items():
            entry = chat_entry(value)
            if entry is not None:
                chats[str(key)] = entry
        self.chats = chats

    def save(self):
        with self.lock:
            payload = {
                "enabled": self.enabled,
                "hours": self.hours,
                "text": self.text,
                "reminded": self.reminded,
                "chats": self.chats,
            }
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.path.with_name(self.path.name + ".tmp")
                temporary.write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )
                os.replace(temporary, self.path)
                self.dirty = False
            except OSError:
                logger.warning("Не удалось сохранить настройки напоминаний.")
                logger.debug("TRACEBACK", exc_info=True)

    def update(self, **values):
        with self.lock:
            for key, value in values.items():
                setattr(self, key, value)
            self.save()

    def observe(self, name, chat_id, author, moment):
        with self.lock:
            self.chats[name] = {"chat_id": chat_id, "author": author, "time": moment}
            self.dirty = True

    def mark(self, order_ids, moment):
        with self.lock:
            for order_id in order_ids:
                self.reminded[str(order_id)] = moment
            self.save()

    def prune(self, now):
        limit = now - REMINDER_KEEP_SECONDS
        with self.lock:
            reminded = {k: v for k, v in self.reminded.items() if v >= limit}
            chats = {k: v for k, v in self.chats.items() if v["time"] >= limit}
            if len(reminded) != len(self.reminded) or len(chats) != len(self.chats):
                self.reminded, self.chats, self.dirty = reminded, chats, True

    def sent_since(self, moment):
        with self.lock:
            return sum(1 for value in self.reminded.values() if value >= moment)
