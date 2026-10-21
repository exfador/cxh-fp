from dataclasses import dataclass, replace
from secrets import token_hex
from threading import Lock
from time import monotonic

from tg_bot.constants.menu import (
    MENU_READ_COOLDOWN,
    MENU_SESSION_LIMIT,
    MENU_SESSION_SECONDS,
    MENU_TOKEN_BYTES,
)


@dataclass(frozen=True)
class MenuSession:
    owner_id: int
    chat_id: int
    message_id: int
    expires_at: float
    query: str = ""
    lot_id: int | None = None
    reading: bool = False
    pending_restart: bool = False
    orders: tuple | None = None
    revision: int = 0
    reads: tuple = ()
    lot_page: int = 0
    order_page: int = 0
    pending_resolution: str = ""


class MenuSessionStore:
    def __init__(self, clock=monotonic, preferences_path=None):
        self.clock = clock
        self.sessions: dict[str, MenuSession] = {}
        self.lock = Lock()
        self.preferences_path = preferences_path
        self.preferences = {}
        if preferences_path:
            from app.updates.store import load_state

            try:
                self.preferences = load_state(preferences_path)
            except (OSError, ValueError):
                pass

    def create(self, owner_id, chat_id, message_id):
        with self.lock:
            now = self.clock()
            self.sessions = {
                token: session
                for token, session in self.sessions.items()
                if session.expires_at > now
            }
            if len(self.sessions) >= MENU_SESSION_LIMIT:
                oldest = min(
                    self.sessions, key=lambda token: self.sessions[token].expires_at
                )
                del self.sessions[oldest]
            token = token_hex(MENU_TOKEN_BYTES)
            while token in self.sessions:
                token = token_hex(MENU_TOKEN_BYTES)
            self.sessions[token] = MenuSession(
                owner_id,
                chat_id,
                message_id,
                now + MENU_SESSION_SECONDS,
                **self.saved_preferences(owner_id)
            )
            return token

    def get(self, token, owner_id, chat_id, message_id=None):
        with self.lock:
            session = self.sessions.get(token)
            if session is None or session.expires_at <= self.clock():
                self.sessions.pop(token, None)
                return None
            if session.owner_id != owner_id or session.chat_id != chat_id:
                return None
            if message_id is not None and session.message_id != message_id:
                return None
            return session

    def update(self, token, **fields):
        with self.lock:
            session = self.sessions.get(token)
            if session is None or session.expires_at <= self.clock():
                return None
            self.sessions[token] = replace(session, **fields)
            if {"query", "lot_page", "order_page"} & fields.keys():
                self.save_preferences(self.sessions[token])
            return self.sessions[token]

    def saved_preferences(self, owner_id):
        row = self.preferences.get(str(owner_id), {})
        if not isinstance(row, dict):
            return {}
        result = {}
        if isinstance(row.get("query"), str) and len(row["query"]) <= 120:
            result["query"] = row["query"]
        for key in ("lot_page", "order_page"):
            if type(row.get(key)) is int and 0 <= row[key] < 100000:
                result[key] = row[key]
        return result

    def save_preferences(self, session):
        self.preferences[str(session.owner_id)] = {
            key: getattr(session, key) for key in ("query", "lot_page", "order_page")
        }
        self.preferences = dict(list(self.preferences.items())[-MENU_SESSION_LIMIT:])
        if self.preferences_path:
            from app.updates.store import write_state

            try:
                write_state(self.preferences_path, self.preferences)
            except (OSError, ValueError):
                pass

    def consume_resolution(self, token, identifier):
        with self.lock:
            session = self.sessions.get(token)
            if (
                session is None
                or session.expires_at <= self.clock()
                or session.pending_resolution != identifier
            ):
                return False
            self.sessions[token] = replace(session, pending_resolution="")
            return True

    def begin_read(self, token, action=""):
        with self.lock:
            session = self.sessions.get(token)
            now = self.clock()
            if session is None or session.expires_at <= now or session.reading:
                return False
            reads = dict(session.reads)
            if now - reads.get(action, float("-inf")) < MENU_READ_COOLDOWN:
                return False
            reads[action] = now
            self.sessions[token] = replace(
                session, reading=True, reads=tuple(reads.items())
            )
            return True

    def finish_read(self, token):
        self.update(token, reading=False)

    def consume_restart(self, token):
        with self.lock:
            session = self.sessions.get(token)
            if (
                session is None
                or session.expires_at <= self.clock()
                or not session.pending_restart
            ):
                return False
            self.sessions[token] = replace(session, pending_restart=False)
            return True

    def advance(self, token):
        with self.lock:
            now = self.clock()
            session = self.sessions.get(token)
            if session is None or session.expires_at <= now:
                return None
            updated = replace(
                session,
                revision=session.revision + 1,
                expires_at=now + MENU_SESSION_SECONDS,
            )
            self.sessions[token] = updated
            return updated.revision
