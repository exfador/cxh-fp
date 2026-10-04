import functools
import inspect
import secrets
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import RLock

import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot.constants.menu import MENU_NOT_MODIFIED
from tg_bot.constants.panel_history import PANEL_HISTORY_TOKEN_BYTES
from tg_bot.constants.panel_navigation import (
    PANEL_BACK_ALIASES,
    PANEL_BUTTON_BACK,
    PANEL_BUTTON_CANCEL,
    PANEL_CALLBACK_PREFIX,
    PANEL_CONTEXT_NAME,
    PANEL_EDIT_METHODS,
    PANEL_LOCK_COUNT,
    PANEL_NATIVE_CALLBACK_ROOTS,
    PANEL_NATIVE_MODULE_ROOTS,
    PANEL_REMOVE_METHOD,
    PANEL_REPLACE_MENU_ACTIONS,
    PANEL_REPLACE_METHOD,
)
from tg_bot.constants.plugin_consent import UPLOAD_CONSENT_PREFIX
from tg_bot.keyboard_appearance import canonical_keyboard, incoming_keyboard
from tg_bot.panel_history import PanelHistory

NATIVE_CBT_ROOTS = frozenset(
    value.split(":", 1)[0]
    for name, value in vars(CBT).items()
    if not name.startswith("_") and isinstance(value, str)
)


def native_handler(handler):
    target = handler
    while True:
        if isinstance(target, functools.partial):
            target = target.func
        elif inspect.ismethod(target):
            target = target.__func__
        else:
            break
    module = getattr(target, "__module__", None) or type(target).__module__ or ""
    return module.split(".", 1)[0] in PANEL_NATIVE_MODULE_ROOTS


@dataclass(frozen=True)
class PanelContext:
    owner_id: int
    chat_id: int
    message_id: int
    replace: bool = False
    home: bool = False
    callback: CallbackQuery | None = None

    @property
    def key(self):
        return self.owner_id, self.chat_id, self.message_id

    @property
    def route(self):
        return self.callback.data if self.callback else None


class PanelNavigation:
    def __init__(self, controller, history=None):
        self.controller = controller
        self.history = history or PanelHistory()
        self.context = ContextVar(PANEL_CONTEXT_NAME, default=None)
        self.locks = tuple(RLock() for _ in range(PANEL_LOCK_COUNT))

    def process_callback(self, handler, call):
        if not call.message or not self.controller.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            self.controller.bot.answer_callback_query(call.id)
            return
        panel = PanelContext(
            call.from_user.id,
            call.message.chat.id,
            call.message.id,
            self.replaces_screen(call.data),
            self.is_home(call.data),
            call,
        )
        with self.locks[hash(panel.key) % PANEL_LOCK_COUNT], self.activate(panel):
            if not self.history.contains(*panel.key):
                self.history.begin(
                    *panel.key,
                    getattr(call.message, "html_text", None) or call.message.text or "",
                    incoming_keyboard(call.message),
                )
            return handler(call)

    def process_message(self, handler, message):
        if not self.controller.menu_user_allowed(message.from_user, message.chat):
            return
        state = self.controller.get_state(message.chat.id, message.from_user.id)
        if not state:
            return handler(message)
        panel = PanelContext(message.from_user.id, message.chat.id, state["mid"], True)
        if not self.history.contains(*panel.key):
            return handler(message)
        with self.locks[hash(panel.key) % PANEL_LOCK_COUNT], self.activate(panel):
            return handler(message)

    @contextmanager
    def activate(self, panel):
        token = self.context.set(panel)
        try:
            yield
        finally:
            self.context.reset(token)

    def replaces_screen(self, callback):
        parts = (callback or "").split(":")
        if parts[0] in {
            CBT.SWITCH,
            CBT.SWITCH_TG_NOTIFICATIONS,
            CBT.LANG,
            CBT.CHAT_SYNC_TOGGLE,
            CBT.CHAT_SYNC_UNBIND,
            CBT.CHAT_SYNC_UNBIND_CONFIRM,
            CBT.CHAT_SYNC_HELPERS_REFRESH,
            CBT.CHAT_SYNC_HELPER_DEL,
            CBT.CONFIRM_REMINDER_TOGGLE,
            CBT.CONFIRM_REMINDER_RESET,
            UPLOAD_CONSENT_PREFIX,
        }:
            return True
        return len(parts) > 2 and parts[2] in PANEL_REPLACE_MENU_ACTIONS

    def is_home(self, callback):
        parts = (callback or "").split(":")
        return (
            callback == CBT.MAIN
            or parts[:2] == ["ops", "home"]
            or len(parts) == 4
            and parts[2] == "home"
        )

    def targets_panel(self, arguments, panel):
        return (
            arguments.get("chat_id") == panel.chat_id
            and arguments.get("message_id", panel.message_id) == panel.message_id
        )

    def request(self, method, args, kwargs, text_field, execute):
        panel = self.context.get()
        bound = inspect.signature(method).bind(self.controller.bot, *args, **kwargs)
        if panel is None or not self.targets_panel(bound.arguments, panel):
            return execute(method, args, kwargs, text_field)
        name = method.__name__
        if name == PANEL_REMOVE_METHOD:
            return True
        if name == PANEL_REPLACE_METHOD:
            return self.edit_markup(panel, bound.arguments, execute)
        if name not in PANEL_EDIT_METHODS:
            return execute(method, args, kwargs, text_field)
        return self.edit_text(panel, bound.arguments, execute)

    def edit_markup(self, panel, arguments, execute):
        snapshot = self.history.current(*panel.key)
        payload = {
            "text": snapshot.text,
            "chat_id": panel.chat_id,
            "message_id": panel.message_id,
            "reply_markup": arguments.get("reply_markup"),
        }
        return self.edit_text(panel, payload, execute, replace=True)

    def edit_text(self, panel, arguments, execute, replace=False):
        parameters = inspect.signature(telebot.TeleBot.edit_message_text).parameters
        payload = {
            key: value
            for key, value in arguments.items()
            if key in parameters and key != "self"
        }
        payload.update(chat_id=panel.chat_id, message_id=panel.message_id)
        canonical = payload.get("reply_markup")
        nonce = secrets.token_hex(PANEL_HISTORY_TOKEN_BYTES)
        payload["reply_markup"] = self.navigation_keyboard(
            canonical, nonce, not panel.home
        )
        try:
            response = execute(telebot.TeleBot.edit_message_text, (), payload, "text")
        except ApiTelegramException as error:
            if MENU_NOT_MODIFIED not in error.description.casefold():
                raise
            response = None
        self.record_screen(panel, payload["text"], canonical, nonce, replace)
        return response

    def record_screen(self, panel, text, markup, nonce, replace):
        if panel.home:
            self.history.begin(*panel.key, text, markup, token=nonce, route=panel.route)
            self.clear_panel_state(panel)
            return
        previous = self.history.checkpoint(*panel.key)
        self.history.capture(
            *panel.key,
            text,
            markup,
            token=nonce,
            replace=replace or panel.replace,
            route=panel.route,
        )
        current = self.history.checkpoint(*panel.key)
        if previous.pages and len(current.pages.snapshots) < len(
            previous.pages.snapshots
        ):
            self.clear_panel_state(panel)

    def navigation_keyboard(self, keyboard, token, allow_back=True):
        result = canonical_keyboard(keyboard) if keyboard else InlineKeyboardMarkup()
        if not allow_back:
            return result
        translate = Localizer().translate
        labels = {
            self.button_label(translate(PANEL_BUTTON_BACK)),
            self.button_label(translate(PANEL_BUTTON_CANCEL)),
        }
        found = False
        for row in result.keyboard:
            for button in row:
                data = button.callback_data or ""
                label = self.button_label(button.text)
                if data.startswith(PANEL_CALLBACK_PREFIX) or (
                    label in labels and self.native_callback(data)
                ):
                    button.callback_data = PANEL_CALLBACK_PREFIX + token
                    found = True
                elif not self.native_callback(data) and (
                    label in labels or label in PANEL_BACK_ALIASES
                ):
                    found = True
        if not found:
            result.row(
                InlineKeyboardButton(
                    translate(PANEL_BUTTON_BACK),
                    callback_data=PANEL_CALLBACK_PREFIX + token,
                )
            )
        return result

    @staticmethod
    def native_callback(data):
        root = data.split(":", 1)[0]
        return (
            not data or root in PANEL_NATIVE_CALLBACK_ROOTS or root in NATIVE_CBT_ROOTS
        )

    def button_label(self, text):
        return "".join(
            character for character in text if character.isalpha()
        ).casefold()

    def go_back(self, call):
        panel = self.context.get()
        if panel is None:
            self.controller.bot.answer_callback_query(call.id)
            return
        checkpoint = self.history.checkpoint(*panel.key)
        snapshot = self.history.back(
            *panel.key, call.data[len(PANEL_CALLBACK_PREFIX) :]
        )
        if snapshot is None:
            self.controller.bot.answer_callback_query(
                call.id, Localizer().translate("menu_expired")
            )
            return
        self.controller.bot.answer_callback_query(call.id)
        self.restore_screen(panel, snapshot, checkpoint)
        self.clear_panel_state(panel)

    def clear_panel_state(self, panel):
        state = self.controller.get_state(panel.chat_id, panel.owner_id)
        if state and state["mid"] == panel.message_id:
            self.controller.clear_state(panel.chat_id, panel.owner_id)

    def restore_screen(self, panel, snapshot, checkpoint):
        try:
            current = self.history.checkpoint(*panel.key)
            keyboard = self.navigation_keyboard(
                snapshot.markup, snapshot.token, len(current.pages.snapshots) > 1
            )
            self.controller.bot._ui_request(
                telebot.TeleBot.edit_message_text,
                (snapshot.text, panel.chat_id, panel.message_id),
                {"reply_markup": keyboard},
                "text",
            )
        except Exception:
            self.history.rollback(checkpoint, token=snapshot.token)
            raise

    def suppress_deletion(self, chat_id, message_id):
        panel = self.context.get()
        return panel is not None and (chat_id, message_id) == (
            panel.chat_id,
            panel.message_id,
        )
