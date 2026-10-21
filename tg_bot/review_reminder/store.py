import json
import logging
import os
from pathlib import Path
from threading import RLock

from tg_bot.constants.review_reminder import (
    REVIEW_REMINDER_DEFAULT_HOURS,
    REVIEW_REMINDER_KEEP_SECONDS,
    REVIEW_REMINDER_LOGGER,
    REVIEW_REMINDER_MAX_AGE_SECONDS,
    REVIEW_REMINDER_MAX_HOURS,
    REVIEW_REMINDER_MIN_HOURS,
    REVIEW_REMINDER_PATH,
    REVIEW_REMINDER_TEXT_LIMIT,
    REVIEW_STATUS_SENT,
    REVIEW_STATUSES,
)

logger = logging.getLogger(REVIEW_REMINDER_LOGGER)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def valid_hours(value):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and REVIEW_REMINDER_MIN_HOURS <= value <= REVIEW_REMINDER_MAX_HOURS
    )


def pending_entry(value):
    if not isinstance(value, dict):
        return None
    buyer, moment = value.get("buyer"), value.get("time")
    if not isinstance(buyer, str) or not buyer.strip() or not is_number(moment):
        return None
    buyer_id = value.get("buyer_id")
    if not isinstance(buyer_id, int) or isinstance(buyer_id, bool):
        buyer_id = None
    chat_id = value.get("chat_id")
    if not isinstance(chat_id, (int, str)) or isinstance(chat_id, bool):
        chat_id = None
    return {
        "buyer": buyer,
        "buyer_id": buyer_id,
        "chat_id": chat_id,
        "time": float(moment),
    }


def done_entry(value):
    if not isinstance(value, dict):
        return None
    status, moment = value.get("status"), value.get("time")
    if status not in REVIEW_STATUSES or not is_number(moment):
        return None
    return {"status": status, "time": float(moment)}


class ReviewReminderStore:
    def __init__(self, path=REVIEW_REMINDER_PATH):
        self.path = Path(path)
        self.lock = RLock()
        self.enabled = False
        self.hours = REVIEW_REMINDER_DEFAULT_HOURS
        self.text = ""
        self.pending = {}
        self.done = {}
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
        self.text = text[:REVIEW_REMINDER_TEXT_LIMIT] if isinstance(text, str) else ""
        self.pending = self.parse(data.get("pending"), pending_entry)
        self.done = self.parse(data.get("done"), done_entry)

    @staticmethod
    def parse(rows, check):
        result = {}
        for key, value in (rows if isinstance(rows, dict) else {}).items():
            entry = check(value)
            if entry is not None:
                result[str(key)] = entry
        return result

    def save(self):
        with self.lock:
            payload = {
                "enabled": self.enabled,
                "hours": self.hours,
                "text": self.text,
                "pending": self.pending,
                "done": self.done,
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
                logger.warning("Не удалось сохранить настройки напоминаний об отзыве.")
                logger.debug("TRACEBACK", exc_info=True)

    def update(self, **values):
        with self.lock:
            for key, value in values.items():
                setattr(self, key, value)
            self.save()

    def add(self, order_id, buyer, buyer_id, chat_id, moment):
        key = str(order_id)
        with self.lock:
            if key in self.pending or key in self.done:
                return False
            entry = pending_entry(
                {
                    "buyer": buyer,
                    "buyer_id": buyer_id,
                    "chat_id": chat_id,
                    "time": moment,
                }
            )
            if entry is None:
                return False
            self.pending[key] = entry
            self.save()
            return True

    def finish(self, order_ids, status, moment):
        if status not in REVIEW_STATUSES:
            raise ValueError("Unknown review reminder status")
        with self.lock:
            for order_id in order_ids:
                key = str(order_id)
                self.pending.pop(key, None)
                self.done[key] = {"status": status, "time": moment}
            self.save()

    def prune(self, now):
        with self.lock:
            done = {
                k: v
                for k, v in self.done.items()
                if v["time"] >= now - REVIEW_REMINDER_KEEP_SECONDS
            }
            pending = {
                k: v
                for k, v in self.pending.items()
                if v["time"] >= now - REVIEW_REMINDER_MAX_AGE_SECONDS
            }
            if len(done) != len(self.done) or len(pending) != len(self.pending):
                self.done, self.pending, self.dirty = done, pending, True

    def sent_since(self, moment):
        with self.lock:
            return sum(
                1
                for value in self.done.values()
                if value["status"] == REVIEW_STATUS_SENT and value["time"] >= moment
            )

    def waiting(self):
        with self.lock:
            return len(self.pending)
