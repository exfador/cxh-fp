import json
import logging
import os
from pathlib import Path
from threading import RLock

from tg_bot.constants.chat_sync import CHAT_SYNC_DEFAULT_OPTIONS, CHAT_SYNC_PATH

logger = logging.getLogger("CoxerHubBot.chat_sync")


class ChatSyncStore:
    def __init__(self, path=CHAT_SYNC_PATH):
        self.path = Path(path)
        self.lock = RLock()
        self.chat_id = None
        self.title = ""
        self.threads = {}
        self.names = {}
        self.icons = {}
        self.options = dict(CHAT_SYNC_DEFAULT_OPTIONS)
        self.helpers = []
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        chat_id = data.get("chat_id")
        self.chat_id = chat_id if isinstance(chat_id, int) else None
        self.title = str(data.get("title") or "")
        self.threads = {
            str(key): int(value)
            for key, value in (data.get("threads") or {}).items()
            if str(value).lstrip("-").isdigit()
        }
        self.names = {
            str(key): str(value) for key, value in (data.get("names") or {}).items()
        }
        self.icons = {
            str(key): str(value) for key, value in (data.get("icons") or {}).items()
        }
        options = data.get("options") or {}
        for key in self.options:
            if isinstance(options.get(key), bool):
                self.options[key] = options[key]
        self.helpers = [
            {
                "token": str(entry["token"]),
                "id": int(entry["id"]),
                "username": str(entry.get("username") or ""),
            }
            for entry in data.get("helpers") or []
            if isinstance(entry, dict)
            and entry.get("token")
            and str(entry.get("id", "")).isdigit()
        ]

    def save(self):
        with self.lock:
            payload = {
                "chat_id": self.chat_id,
                "title": self.title,
                "threads": self.threads,
                "names": self.names,
                "icons": self.icons,
                "options": self.options,
                "helpers": self.helpers,
            }
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.path.with_name(self.path.name + ".tmp")
                temporary.write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )
                os.replace(temporary, self.path)
            except OSError:
                logger.warning("Не удалось сохранить настройки синхронизации чатов.")
                logger.debug("TRACEBACK", exc_info=True)

    def bind(self, chat_id, title):
        with self.lock:
            if chat_id != self.chat_id:
                self.threads.clear()
                self.names.clear()
                self.icons.clear()
            self.chat_id, self.title = chat_id, title or ""
            self.save()

    def unbind(self):
        with self.lock:
            self.chat_id, self.title = None, ""
            self.threads.clear()
            self.names.clear()
            self.icons.clear()
            self.save()

    def rename(self, title):
        with self.lock:
            if title and title != self.title:
                self.title = title
                self.save()

    def thread_for(self, fp_chat_id):
        with self.lock:
            return self.threads.get(str(fp_chat_id))

    def chat_for(self, thread_id):
        with self.lock:
            for key, value in self.threads.items():
                if value == thread_id:
                    return key, self.names.get(key)
        return None

    def remember(self, fp_chat_id, name, thread_id):
        with self.lock:
            key = str(fp_chat_id)
            self.threads[key] = int(thread_id)
            if name:
                self.names[key] = name
            self.save()

    def forget(self, fp_chat_id):
        with self.lock:
            key = str(fp_chat_id)
            thread = self.threads.pop(key, None)
            self.names.pop(key, None)
            self.icons.pop(str(thread), None)
            self.save()

    def icon(self, thread_id):
        with self.lock:
            return self.icons.get(str(thread_id))

    def set_icon(self, thread_id, icon):
        with self.lock:
            self.icons[str(thread_id)] = icon
            self.save()

    def option(self, key):
        with self.lock:
            return bool(self.options.get(key, CHAT_SYNC_DEFAULT_OPTIONS.get(key)))

    def toggle(self, key):
        with self.lock:
            if key not in self.options:
                return None
            self.options[key] = not self.options[key]
            self.save()
            return self.options[key]

    def helper_entries(self):
        with self.lock:
            return [dict(entry) for entry in self.helpers]

    def add_helper(self, token, user_id, username):
        with self.lock:
            self.helpers.append(
                {"token": token, "id": int(user_id), "username": username or ""}
            )
            self.save()

    def remove_helper(self, user_id):
        with self.lock:
            for index, entry in enumerate(self.helpers):
                if entry["id"] == user_id:
                    removed = self.helpers.pop(index)
                    self.save()
                    return removed
        return None
