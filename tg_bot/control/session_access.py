from __future__ import annotations
from contextlib import nullcontext
from typing import TYPE_CHECKING
from tg_bot.utils import NotificationTypes
from tg_bot.constants.notification_policy import (
    DEFAULT_ENABLED_NOTIFICATION_TYPES,
    DISABLED_NOTIFICATION_TYPES,
)
from tg_bot.constants.panel_navigation import PLUGIN_PANEL_OPTION, PLUGIN_PANEL_SECTION
from tg_bot.panel_navigation import native_handler
from cardinal_core.plugin_context import active_plugin, module_matches

if TYPE_CHECKING:
    pass
from telebot.types import Message, CallbackQuery
from tg_bot import utils, static_keyboards as skb, CBT
from Utils import cardinal_tools
import tg_bot.bot as _module_state


class SessionAccess:
    def get_state(self, chat_id: int, user_id: int) -> dict | None:
        try:
            return self.user_states[chat_id][user_id]
        except KeyError:
            return None

    def set_state(
        self,
        chat_id: int,
        message_id: int,
        user_id: int,
        state: str,
        data: dict | None = None,
    ):
        if chat_id not in self.user_states:
            self.user_states[chat_id] = {}
        self.user_states[chat_id][user_id] = {
            "state": state,
            "mid": message_id,
            "data": data or {},
        }

    def clear_state(
        self, chat_id: int, user_id: int, del_msg: bool = False
    ) -> int | None:
        try:
            state = self.user_states[chat_id][user_id]
        except KeyError:
            return None
        msg_id = state.get("mid")
        del self.user_states[chat_id][user_id]
        if del_msg:
            try:
                self.bot.delete_message(chat_id, msg_id)
            except:
                pass
        return msg_id

    def check_state(self, chat_id: int, user_id: int, state: str) -> bool:
        try:
            return self.user_states[chat_id][user_id]["state"] == state
        except KeyError:
            return False

    def is_notification_enabled(
        self, chat_id: int | str, notification_type: str
    ) -> bool:
        if notification_type in DISABLED_NOTIFICATION_TYPES:
            return False
        try:
            return bool(self.notification_settings[str(chat_id)][notification_type])
        except KeyError:
            return (
                notification_type in DEFAULT_ENABLED_NOTIFICATION_TYPES
                and str(chat_id) in self.notification_settings
            )

    def toggle_notification(self, chat_id: int, notification_type: str) -> bool:
        if (
            notification_type in DISABLED_NOTIFICATION_TYPES
            or not self.notification_recipient_allowed(chat_id)
        ):
            return False
        chat_id = str(chat_id)
        if chat_id not in self.notification_settings:
            self.notification_settings[chat_id] = {}
        self.notification_settings[chat_id][
            notification_type
        ] = not self.is_notification_enabled(chat_id, notification_type)
        utils.save_notification_settings(self.notification_settings)
        return self.notification_settings[chat_id][notification_type]

    def notification_recipient_allowed(self, chat_id):
        try:
            recipient = int(chat_id)
        except (ValueError, TypeError):
            return False
        return (
            recipient > 0
            and str(recipient) == str(chat_id)
            and recipient in self.authorized_users
        )

    def is_file_handler(self, m: Message):
        return self.get_state(m.chat.id, m.from_user.id) and m.content_type in [
            "photo",
            "document",
        ]

    def file_handler(self, state, handler):
        self.file_handlers[state] = handler
        self.__dict__.setdefault("file_handler_owners", {})[state] = active_plugin()

    def handler_owned(self, function, uuid, modules):
        if getattr(function, "cxh_plugin", None) == uuid:
            return True
        target = getattr(function, "cxh_target", function)
        return module_matches(getattr(target, "__module__", ""), modules)

    def forget_plugin_handlers(self, uuid, modules=()):
        def keep(item):
            function = item.get("function") if isinstance(item, dict) else item
            return not callable(function) or not self.handler_owned(
                function, uuid, modules
            )

        removed = 0
        for value in vars(self.bot).values():
            groups = value.values() if isinstance(value, dict) else [value]
            for group in groups:
                if isinstance(group, list):
                    before = len(group)
                    group[:] = [item for item in group if keep(item)]
                    removed += before - len(group)
        owners = self.__dict__.setdefault("file_handler_owners", {})
        for state, handler in list(self.file_handlers.items()):
            if owners.get(state) == uuid or module_matches(
                getattr(handler, "__module__", ""), modules
            ):
                self.file_handlers.pop(state)
                owners.pop(state, None)
                removed += 1
        return removed

    def run_file_handlers(self, m: Message):
        if (state := self.get_state(m.chat.id, m.from_user.id)) is None or state[
            "state"
        ] not in self.file_handlers:
            return
        try:
            handler = self.file_handlers[state["state"]]
            if native_handler(handler):
                handler(m)
            else:
                with self.plugin_scope():
                    handler(m)
            section = state["data"].get("operator_return")
            if section and self.get_state(m.chat.id, m.from_user.id) is None:
                self.operator_complete(m, section)
        except:
            _module_state.logger.error(_module_state._("log_tg_handler_error"))
            _module_state.logger.debug("TRACEBACK", exc_info=True)

    def plugin_panel_enabled(self) -> bool:
        try:
            return self.cardinal.MAIN_CFG[PLUGIN_PANEL_SECTION].getboolean(
                PLUGIN_PANEL_OPTION, fallback=False
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

    def plugin_user_allowed(self, user) -> bool:
        return user is not None and user.id in self.authorized_users

    def plugin_scope(self):
        navigation = getattr(self, "panel_navigation", None)
        if navigation is None or self.plugin_panel_enabled():
            return nullcontext()
        return navigation.activate(None)

    def msg_handler(self, handler, **kwargs):
        bot_instance = self.bot
        native = native_handler(handler)

        @bot_instance.message_handler(**kwargs)
        def run_handler(message: Message):
            try:
                if handler == self.reg_admin:
                    return handler(message)
                if not native and not self.plugin_panel_enabled():
                    if self.plugin_user_allowed(message.from_user):
                        self.bot.emoji_policy.observe(message.from_user)
                        handler(message)
                    return
                if not self.menu_user_allowed(message.from_user, message.chat):
                    return
                self.bot.emoji_policy.observe(message.from_user)
                navigation = getattr(self, "panel_navigation", None)
                if navigation is None:
                    handler(message)
                else:
                    navigation.process_message(handler, message)
            except:
                _module_state.logger.error(_module_state._("log_tg_handler_error"))
                _module_state.logger.debug("TRACEBACK", exc_info=True)

        run_handler.cxh_plugin, run_handler.cxh_target = active_plugin(), handler

    def cbq_handler(self, handler, func, **kwargs):
        bot_instance = self.bot
        native = native_handler(handler)

        @bot_instance.callback_query_handler(func, **kwargs)
        def run_handler(call: CallbackQuery):
            try:
                if handler == self.ignore_unauthorized_users:
                    return handler(call)
                if not native and not self.plugin_panel_enabled():
                    if not self.plugin_user_allowed(call.from_user):
                        self.bot.answer_callback_query(call.id)
                        return
                    self.bot.emoji_policy.observe(call.from_user)
                    handler(call)
                    return
                if not call.message or not self.menu_user_allowed(
                    call.from_user, call.message.chat
                ):
                    self.bot.answer_callback_query(call.id)
                    return
                self.bot.emoji_policy.observe(call.from_user)
                navigation = getattr(self, "panel_navigation", None)
                if navigation is None:
                    handler(call)
                else:
                    navigation.process_callback(handler, call)
            except:
                _module_state.logger.error(_module_state._("log_tg_handler_error"))
                _module_state.logger.debug("TRACEBACK", exc_info=True)

        run_handler.cxh_plugin, run_handler.cxh_target = active_plugin(), handler

    def mdw_handler(self, handler, **kwargs):
        bot_instance = self.bot

        @bot_instance.middleware_handler(**kwargs)
        def run_handler(bot, update):
            try:
                handler(bot, update)
            except:
                _module_state.logger.error(_module_state._("log_tg_handler_error"))
                _module_state.logger.debug("TRACEBACK", exc_info=True)

        run_handler.cxh_plugin, run_handler.cxh_target = active_plugin(), handler

    def setup_chat_notifications(self, bot: _module_state.TGBot, m: Message):
        if not self.menu_user_allowed(m.from_user, m.chat):
            return
        chat_id = str(m.chat.id)
        if chat_id not in self.notification_settings:
            self.notification_settings[chat_id] = (
                self._TGBot__default_notification_settings.copy()
            )
        elif self.is_notification_enabled(m.chat.id, NotificationTypes.critical):
            return
        else:
            self.notification_settings[chat_id][NotificationTypes.critical] = 1
        utils.save_notification_settings(self.notification_settings)

    def reg_admin(self, m: Message):
        lang = m.from_user.language_code
        if (
            m.chat.type != "private"
            or m.chat.id != m.from_user.id
            or self.attempts.get(m.from_user.id, 0) >= 5
            or m.text is None
        ):
            return
        if not self.cardinal.block_tg_login and cardinal_tools.check_password(
            m.text, self.cardinal.MAIN_CFG["Telegram"]["secretKeyHash"]
        ):
            self.send_notification(
                text=_module_state._(
                    "access_granted_notification", m.from_user.username, m.from_user.id
                ),
                notification_type=NotificationTypes.critical,
                pin=True,
            )
            self.authorized_users[m.from_user.id] = {}
            utils.save_authorized_users(self.authorized_users)
            if str(
                m.chat.id
            ) not in self.notification_settings or not self.is_notification_enabled(
                m.chat.id, NotificationTypes.critical
            ):
                self.notification_settings[str(m.chat.id)] = (
                    self._TGBot__default_notification_settings.copy()
                )
                self.notification_settings[str(m.chat.id)][
                    NotificationTypes.critical
                ] = 1
                utils.save_notification_settings(self.notification_settings)
            text = _module_state._("access_granted", language=lang)
            kb_links = None
            _module_state.logger.warning(
                _module_state._(
                    "log_access_granted", m.from_user.username, m.from_user.id
                )
            )
        else:
            self.attempts[m.from_user.id] = self.attempts.get(m.from_user.id, 0) + 1
            text = _module_state._("access_denied", m.from_user.username, language=lang)
            kb_links = None
            _module_state.logger.warning(
                _module_state._(
                    "log_access_attempt", m.from_user.username, m.from_user.id
                )
            )
        self.bot.send_message(m.chat.id, text, reply_markup=kb_links)

    def ignore_unauthorized_users(self, c: CallbackQuery):
        _module_state.logger.warning(
            _module_state._(
                "log_click_attempt",
                c.from_user.username,
                c.from_user.id,
                c.message.chat.username,
                c.message.chat.id,
            )
        )
        self.attempts[c.from_user.id] = self.attempts.get(c.from_user.id, 0) + 1
        if self.attempts[c.from_user.id] <= 5:
            self.bot.answer_callback_query(c.id)
        return

    def send_settings_menu(self, m: Message):
        self.send_home_menu(m)

    def send_profile(self, m: Message):
        self.bot.send_message(
            m.chat.id,
            utils.generate_profile_text(self.cardinal),
            reply_markup=skb.REFRESH_BTN(),
        )

    def act_change_cookie(self, m: Message):
        result = self.bot.send_message(
            m.chat.id,
            _module_state._("act_change_golden_key"),
            reply_markup=skb.CLEAR_STATE_BTN(),
        )
        self.set_state(m.chat.id, result.id, m.from_user.id, CBT.CHANGE_GOLDEN_KEY)
