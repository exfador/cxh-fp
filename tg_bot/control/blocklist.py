import hashlib
import logging
import secrets
import time
import unicodedata
from html import escape

from telebot.types import InlineKeyboardMarkup

from locales.localizer import Localizer
from tg_bot.constants.blocklist import (
    BLOCKLIST_CALLBACK_HANDLERS,
    BLOCKLIST_CONFIRM_SECONDS,
    BLOCKLIST_CONFIRM_STATE,
    BLOCKLIST_HASH_LENGTH,
    BLOCKLIST_INPUT_SECONDS,
    BLOCKLIST_INPUT_STATE,
    BLOCKLIST_LABEL_LENGTH,
    BLOCKLIST_NAME_LENGTH,
)
from tg_bot.constants.operator import OPERATOR_FAILURE_LOG, OPERATOR_LOGGER
from tg_bot.keyboard_views.operator import operator_button, operator_navigation
from tg_bot.menu_data import menu_page
from Utils import cardinal_tools


def nickname_key(nickname):
    return hashlib.sha256(nickname.encode("utf-8")).hexdigest()[:BLOCKLIST_HASH_LENGTH]


def validate_nickname(text):
    if not isinstance(text, str):
        raise ValueError("Nickname must be text")
    nickname = unicodedata.normalize("NFKC", text).strip()
    if not nickname or len(nickname) > BLOCKLIST_NAME_LENGTH:
        raise ValueError("Invalid nickname length")
    if not nickname.isprintable() or any(char.isspace() for char in nickname):
        raise ValueError("Invalid nickname characters")
    if nickname.startswith("/"):
        raise ValueError("Nickname cannot be a bot command")
    return nickname


class BlocklistPanel:
    def blocklist_callback(self, call, action, argument):
        if not call.message or not self.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            return
        method = BLOCKLIST_CALLBACK_HANDLERS.get(action)
        if method is None:
            raise ValueError("Unsupported blocklist action")
        getattr(self, method)(call, argument)

    def blocklist_list(self, call, argument=None):
        self.clear_state(call.message.chat.id, call.from_user.id)
        names = sorted(self.cardinal.blacklist, key=str.casefold)
        items, page = menu_page(names, argument or "0")
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            operator_button("operator_bl_add", "bl_add"),
            operator_button("operator_bl_remove", "bl_remove"),
        )
        for name in items:
            button = operator_button(
                "operator_bl_remove", "bl_select", nickname_key(name)
            )
            button.text = name[:BLOCKLIST_LABEL_LENGTH]
            keyboard.row(button)
        self.blocklist_pages(keyboard, page, len(names))
        keyboard.keyboard.extend(operator_navigation().keyboard)
        title = Localizer().translate("operator_bl_title")
        content = "\n".join(
            f"<code>{escape(name[:BLOCKLIST_NAME_LENGTH])}</code>" for name in items
        )
        text = title + "\n\n" + (content or Localizer().translate("operator_bl_empty"))
        self.bot.edit_message_text(
            text, call.message.chat.id, call.message.id, reply_markup=keyboard
        )

    def blocklist_pages(self, keyboard, page, total):
        from tg_bot.constants.menu import MENU_PAGE_SIZE

        buttons = []
        if page:
            buttons.append(operator_button("menu_previous_button", "bl_list", page - 1))
        if (page + 1) * MENU_PAGE_SIZE < total:
            buttons.append(operator_button("menu_next_button", "bl_list", page + 1))
        if buttons:
            keyboard.row(*buttons)

    def blocklist_add(self, call, argument=None):
        self.blocklist_prompt(call, "add", "act_blacklist")

    def blocklist_remove(self, call, argument=None):
        self.blocklist_prompt(call, "remove", "operator_bl_remove_prompt")

    def blocklist_prompt(self, call, mode, text_key):
        sent = self.bot.send_message(
            call.message.chat.id,
            Localizer().translate(text_key),
            reply_markup=operator_navigation("blacklist"),
        )
        self.set_state(
            call.message.chat.id,
            sent.id,
            call.from_user.id,
            BLOCKLIST_INPUT_STATE,
            {"mode": mode, "created": time.monotonic()},
        )

    def blocklist_input(self, message):
        if not self.menu_user_allowed(message.from_user, message.chat):
            return
        state = self.get_state(message.chat.id, message.from_user.id)
        if state is None or state["state"] != BLOCKLIST_INPUT_STATE:
            return
        if time.monotonic() - state["data"]["created"] >= BLOCKLIST_INPUT_SECONDS:
            self.clear_state(message.chat.id, message.from_user.id)
            self.blocklist_reply(message.chat.id, "menu_expired")
            return
        try:
            nickname = validate_nickname(message.text)
        except ValueError:
            self.blocklist_reply(message.chat.id, "operator_bl_invalid")
            return
        try:
            self.blocklist_apply_input(message, state["data"]["mode"], nickname)
        except OSError as error:
            logging.getLogger(OPERATOR_LOGGER).warning(
                OPERATOR_FAILURE_LOG, "bl_add", type(error).__name__
            )
            self.blocklist_reply(message.chat.id, "menu_action_error")

    def blocklist_apply_input(self, message, mode, nickname):
        with self.process_action_lock:
            matches = [
                name
                for name in self.cardinal.blacklist
                if name.casefold() == nickname.casefold()
            ]
            if mode == "add" and matches:
                self.blocklist_reply(message.chat.id, "operator_bl_exists", nickname)
                return
            if mode == "remove" and not matches:
                self.blocklist_reply(message.chat.id, "operator_bl_missing", nickname)
                return
            if mode == "remove":
                self.clear_state(message.chat.id, message.from_user.id)
                self.blocklist_ask_removal(
                    message.chat.id, message.from_user.id, matches[0]
                )
                return
            if mode != "add":
                raise ValueError("Unsupported blocklist input")
            updated = [*self.cardinal.blacklist, nickname]
            cardinal_tools.cache_blacklist(updated)
            self.cardinal.blacklist[:] = updated
            self.clear_state(message.chat.id, message.from_user.id)
        self.blocklist_reply(message.chat.id, "operator_bl_added", nickname)

    def blocklist_select(self, call, argument):
        matches = [
            name for name in self.cardinal.blacklist if nickname_key(name) == argument
        ]
        if len(matches) != 1:
            self.blocklist_list(call)
            return
        self.blocklist_ask_removal(call.message.chat.id, call.from_user.id, matches[0])

    def blocklist_ask_removal(self, chat_id, user_id, nickname):
        nonce = secrets.token_hex(BLOCKLIST_HASH_LENGTH)
        keyboard = InlineKeyboardMarkup().row(
            operator_button("operator_bl_confirm", "bl_confirm", nonce),
            operator_button("gl_cancel", "bl_list"),
        )
        text = (
            Localizer().translate("operator_bl_confirm")
            + "\n\n"
            + f"<code>{escape(nickname[:BLOCKLIST_NAME_LENGTH])}</code>"
        )
        sent = self.bot.send_message(chat_id, text, reply_markup=keyboard)
        self.set_state(
            chat_id,
            sent.id,
            user_id,
            BLOCKLIST_CONFIRM_STATE,
            {"name": nickname, "nonce": nonce, "created": time.monotonic()},
        )

    def blocklist_confirm(self, call, argument):
        with self.process_action_lock:
            state = self.get_state(call.message.chat.id, call.from_user.id)
            if not self.blocklist_confirmation_valid(state, call, argument):
                return
            name = state["data"]["name"]
            if name not in self.cardinal.blacklist:
                self.clear_state(call.message.chat.id, call.from_user.id)
                return
            updated = list(self.cardinal.blacklist)
            updated.remove(name)
            cardinal_tools.cache_blacklist(updated)
            self.cardinal.blacklist[:] = updated
            self.clear_state(call.message.chat.id, call.from_user.id)
        self.blocklist_reply(call.message.chat.id, "operator_bl_removed", name)

    def blocklist_confirmation_valid(self, state, call, argument):
        if state is None or state["state"] != BLOCKLIST_CONFIRM_STATE:
            return False
        if not isinstance(argument, str) or not argument.isascii():
            return False
        age = time.monotonic() - state["data"]["created"]
        return (
            state["mid"] == call.message.id
            and secrets.compare_digest(state["data"]["nonce"], argument)
            and 0 <= age < BLOCKLIST_CONFIRM_SECONDS
        )

    def blocklist_reply(self, chat_id, key, nickname=""):
        text = Localizer().translate(key, escape(nickname))
        self.bot.send_message(
            chat_id, text, reply_markup=operator_navigation("blacklist")
        )
