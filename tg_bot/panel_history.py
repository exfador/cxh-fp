from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import replace as replace_dataclass
from secrets import compare_digest, token_hex
from threading import RLock
from time import monotonic

from telebot.types import InlineKeyboardMarkup

from tg_bot.constants.panel_history import (
    PANEL_HISTORY_BACK_PREFIX,
    PANEL_HISTORY_CALLBACK_SEPARATOR,
    PANEL_HISTORY_PAGE_LIMIT,
    PANEL_HISTORY_PANEL_LIMIT,
    PANEL_HISTORY_SECONDS,
    PANEL_HISTORY_TOKEN_BYTES,
)


@dataclass(frozen=True)
class PanelSnapshot:
    owner_id: int
    chat_id: int
    message_id: int
    text: str
    markup: InlineKeyboardMarkup | dict[str, object] | None
    token: str

    @property
    def back_callback(self):
        return PANEL_HISTORY_CALLBACK_SEPARATOR.join(
            (PANEL_HISTORY_BACK_PREFIX, self.token)
        )

    @property
    def key(self):
        return self.owner_id, self.chat_id, self.message_id


@dataclass(frozen=True)
class PanelPages:
    snapshots: tuple[PanelSnapshot, ...]
    expires_at: float


@dataclass(frozen=True)
class PanelCheckpoint:
    key: tuple[int, int, int]
    pages: PanelPages | None


def keyboard_content(markup):
    content = markup.to_dict() if hasattr(markup, "to_dict") else deepcopy(markup)
    if not isinstance(content, dict):
        return content
    prefix = PANEL_HISTORY_BACK_PREFIX + PANEL_HISTORY_CALLBACK_SEPARATOR
    rows = content.get("inline_keyboard", [])
    content["inline_keyboard"] = [
        [
            button
            for button in row
            if not button.get("callback_data", "").startswith(prefix)
        ]
        for row in rows
    ]
    content["inline_keyboard"] = [row for row in content["inline_keyboard"] if row]
    return content


def same_presentation(first, second):
    return first.text == second.text and keyboard_content(
        first.markup
    ) == keyboard_content(second.markup)


class PanelHistory:
    def __init__(self, clock=monotonic):
        self.clock = clock
        self.panels: OrderedDict[tuple[int, int, int], PanelPages] = OrderedDict()
        self.lock = RLock()

    def begin(self, owner_id, chat_id, message_id, text, markup, *, token=None):
        snapshot = self.create_snapshot(
            owner_id, chat_id, message_id, text, markup, token
        )
        with self.lock:
            self.remove_expired()
            self.store(snapshot.key, (snapshot,))
            return deepcopy(snapshot)

    def capture(
        self, owner_id, chat_id, message_id, text, markup, *, token=None, replace=False
    ):
        snapshot = self.create_snapshot(
            owner_id, chat_id, message_id, text, markup, token
        )
        with self.lock:
            self.remove_expired()
            pages = self.panels.get(snapshot.key)
            if pages is None:
                self.store(snapshot.key, (snapshot,))
                return deepcopy(snapshot)
            return self.advance(snapshot, token=token, replace=replace)

    def advance(self, snapshot, *, token=None, replace=False):
        with self.lock:
            self.remove_expired()
            pages = self.panels.get(snapshot.key)
            if pages is None:
                raise ValueError("Panel history is unavailable")
            next_snapshot = replace_dataclass(
                deepcopy(snapshot), token=self.resolve_token(token)
            )
            if replace or same_presentation(pages.snapshots[-1], snapshot):
                next_snapshot = replace_dataclass(
                    next_snapshot, token=token or pages.snapshots[-1].token
                )
                self.store(snapshot.key, (*pages.snapshots[:-1], next_snapshot))
                return deepcopy(next_snapshot)
            snapshots = (*pages.snapshots, next_snapshot)[-PANEL_HISTORY_PAGE_LIMIT:]
            self.store(snapshot.key, snapshots)
            return deepcopy(next_snapshot)

    def current(self, owner_id, chat_id, message_id):
        with self.lock:
            self.remove_expired()
            pages = self.panels.get((owner_id, chat_id, message_id))
            return deepcopy(pages.snapshots[-1]) if pages else None

    def contains(self, owner_id, chat_id, message_id):
        return self.current(owner_id, chat_id, message_id) is not None

    def back(self, owner_id, chat_id, message_id, token):
        with self.lock:
            self.remove_expired()
            key = owner_id, chat_id, message_id
            pages = self.panels.get(key)
            if pages is None or len(pages.snapshots) < 2:
                return None
            if not self.token_matches(pages.snapshots[-1].token, token):
                return None
            previous = replace_dataclass(pages.snapshots[-2], token=self.create_token())
            self.store(key, (*pages.snapshots[:-2], previous))
            return deepcopy(previous)

    def forget(self, owner_id, chat_id, message_id):
        with self.lock:
            self.remove_expired()
            return self.panels.pop((owner_id, chat_id, message_id), None) is not None

    def checkpoint(self, owner_id, chat_id, message_id):
        with self.lock:
            self.remove_expired()
            key = owner_id, chat_id, message_id
            return PanelCheckpoint(key, deepcopy(self.panels.get(key)))

    def rollback(self, checkpoint, *, token=None):
        with self.lock:
            self.remove_expired()
            current = self.panels.get(checkpoint.key)
            if token is not None and (
                current is None
                or not self.token_matches(current.snapshots[-1].token, token)
            ):
                return False
            if checkpoint.pages is None:
                return self.panels.pop(checkpoint.key, None) is not None
            if checkpoint.pages.expires_at <= self.clock():
                return False
            self.panels[checkpoint.key] = deepcopy(checkpoint.pages)
            self.panels.move_to_end(checkpoint.key)
            while len(self.panels) > PANEL_HISTORY_PANEL_LIMIT:
                self.panels.popitem(last=False)
            return True

    def create_snapshot(self, owner_id, chat_id, message_id, text, markup, token=None):
        return PanelSnapshot(
            owner_id,
            chat_id,
            message_id,
            text,
            deepcopy(markup),
            self.resolve_token(token),
        )

    def create_token(self):
        return token_hex(PANEL_HISTORY_TOKEN_BYTES)

    def resolve_token(self, token):
        if token is None:
            return self.create_token()
        if not self.token_matches(token, token):
            raise ValueError("Invalid panel token")
        return token

    def token_matches(self, expected, provided):
        if not isinstance(provided, str) or not provided.isascii():
            return False
        if len(provided) != PANEL_HISTORY_TOKEN_BYTES * 2:
            return False
        return compare_digest(expected, provided)

    def store(self, key, snapshots):
        self.panels[key] = PanelPages(snapshots, self.clock() + PANEL_HISTORY_SECONDS)
        self.panels.move_to_end(key)
        while len(self.panels) > PANEL_HISTORY_PANEL_LIMIT:
            self.panels.popitem(last=False)

    def remove_expired(self):
        now = self.clock()
        expired = [key for key, pages in self.panels.items() if pages.expires_at <= now]
        for key in expired:
            del self.panels[key]
