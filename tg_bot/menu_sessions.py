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


class MenuSessionStore:
    def __init__(self, clock=monotonic):
        self.clock = clock
        self.sessions: dict[str, MenuSession] = {}
        self.lock = Lock()

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
                owner_id, chat_id, message_id, now + MENU_SESSION_SECONDS
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
            return self.sessions[token]

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
