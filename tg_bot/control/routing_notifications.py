from __future__ import annotations
from typing import TYPE_CHECKING
from tg_bot.constants.notification_policy import DISABLED_NOTIFICATION_TYPES
from app.constants.languages import REMOVED_LANGUAGE
from tg_bot.constants.menu import MENU_PREFIX, MENU_INPUT_STATE
from tg_bot.constants.blocklist import BLOCKLIST_INPUT_STATE
from tg_bot.constants.operator import OPERATOR_PREFIX
from tg_bot.constants.panel_navigation import PANEL_CALLBACK_PREFIX
from contextlib import nullcontext

if TYPE_CHECKING:
    pass
import time
from telebot.apihelper import ApiTelegramException
import logging
from telebot.types import InlineKeyboardMarkup as K, BotCommand
from tg_bot import utils, CBT
import tg_bot.bot as _module_state


class RoutingNotifications:
    def _TGBot__register_handlers(self):
        self.mdw_handler(self.setup_chat_notifications, update_types=["message"])
        self.msg_handler(
            self.reg_admin,
            func=lambda msg: msg.from_user.id not in self.authorized_users,
            content_types=["text", "document", "photo", "sticker"],
        )
        self.cbq_handler(
            self.ignore_unauthorized_users,
            lambda c: c.from_user.id not in self.authorized_users,
        )
        self.cbq_handler(
            self.panel_navigation.go_back,
            lambda call: (call.data or "").startswith(PANEL_CALLBACK_PREFIX),
        )
        self.cbq_handler(
            self.param_disabled, lambda c: c.data.startswith(CBT.PARAM_DISABLED)
        )
        self.msg_handler(
            self.run_file_handlers,
            content_types=["photo", "document"],
            func=lambda m: self.is_file_handler(m),
        )
        self.msg_handler(self.send_settings_menu, commands=["menu", "start"])
        self.msg_handler(self.restart_cardinal, commands=["restart"])
        self.msg_handler(
            self.send_unknown_command,
            content_types=["text"],
            func=lambda message: bool(message.text) and message.text.startswith("/"),
        )
        self.cbq_handler(
            self.operator_callback,
            lambda call: (call.data or "").startswith(f"{OPERATOR_PREFIX}:"),
        )
        self.msg_handler(
            self.blocklist_input,
            content_types=["text"],
            func=lambda message: self.check_state(
                message.chat.id, message.from_user.id, BLOCKLIST_INPUT_STATE
            ),
        )
        self.cbq_handler(
            self.menu_callback, lambda c: (c.data or "").startswith(f"{MENU_PREFIX}:")
        )
        self.msg_handler(
            self.menu_input_message,
            content_types=["text"],
            func=lambda m: (
                bool(m.text)
                and not m.text.startswith("/")
                and self.check_state(m.chat.id, m.from_user.id, MENU_INPUT_STATE)
            ),
        )
        self.msg_handler(
            self.operator_input,
            func=lambda m: self.check_state(
                m.chat.id, m.from_user.id, CBT.CHANGE_GOLDEN_KEY
            ),
        )
        self.cbq_handler(self.update_profile, lambda c: c.data == CBT.UPDATE_PROFILE)
        self.cbq_handler(
            self.act_edit_greetings_text, lambda c: c.data == CBT.EDIT_GREETINGS_TEXT
        )
        self.msg_handler(
            self.edit_greetings_text,
            func=lambda m: self.check_state(
                m.chat.id, m.from_user.id, CBT.EDIT_GREETINGS_TEXT
            ),
        )
        self.cbq_handler(
            self.act_edit_greetings_cooldown,
            lambda c: c.data == CBT.EDIT_GREETINGS_COOLDOWN,
        )
        self.msg_handler(
            self.edit_greetings_cooldown,
            func=lambda m: self.check_state(
                m.chat.id, m.from_user.id, CBT.EDIT_GREETINGS_COOLDOWN
            ),
        )
        self.cbq_handler(
            self.act_edit_order_confirm_reply_text,
            lambda c: c.data == CBT.EDIT_ORDER_CONFIRM_REPLY_TEXT,
        )
        self.msg_handler(
            self.edit_order_confirm_reply_text,
            func=lambda m: self.check_state(
                m.chat.id, m.from_user.id, CBT.EDIT_ORDER_CONFIRM_REPLY_TEXT
            ),
        )
        self.cbq_handler(
            self.act_edit_review_reply_text,
            lambda c: c.data.startswith(f"{CBT.EDIT_REVIEW_REPLY_TEXT}:"),
        )
        self.msg_handler(
            self.edit_review_reply_text,
            func=lambda m: self.check_state(
                m.chat.id, m.from_user.id, CBT.EDIT_REVIEW_REPLY_TEXT
            ),
        )
        self.msg_handler(
            self.operator_input,
            func=lambda m: self.check_state(
                m.chat.id, m.from_user.id, CBT.MANUAL_AD_TEST
            ),
        )
        self.msg_handler(
            self.ban,
            func=lambda m: self.check_state(m.chat.id, m.from_user.id, CBT.BAN),
        )
        self.msg_handler(
            self.unban,
            func=lambda m: self.check_state(m.chat.id, m.from_user.id, CBT.UNBAN),
        )
        self.msg_handler(
            self.operator_input,
            func=lambda m: self.check_state(
                m.chat.id, m.from_user.id, CBT.EDIT_WATERMARK
            ),
        )
        self.cbq_handler(
            self.send_review_reply_text,
            lambda c: c.data.startswith(f"{CBT.SEND_REVIEW_REPLY_TEXT}:"),
        )
        self.cbq_handler(
            self.act_send_funpay_message,
            lambda c: c.data.startswith(f"{CBT.SEND_FP_MESSAGE}:"),
        )
        self.cbq_handler(
            self.open_reply_menu,
            lambda c: c.data.startswith(f"{CBT.BACK_TO_REPLY_KB}:"),
        )
        self.cbq_handler(
            self.extend_new_message_notification,
            lambda c: c.data.startswith(f"{CBT.EXTEND_CHAT}:"),
        )
        self.msg_handler(
            self.send_funpay_message,
            func=lambda m: self.check_state(
                m.chat.id, m.from_user.id, CBT.SEND_FP_MESSAGE
            ),
        )
        self.cbq_handler(
            self.ask_confirm_refund,
            lambda c: c.data.startswith(f"{CBT.REQUEST_REFUND}:"),
        )
        self.cbq_handler(
            self.cancel_refund, lambda c: c.data.startswith(f"{CBT.REFUND_CANCELLED}:")
        )
        self.cbq_handler(
            self.refund, lambda c: c.data.startswith(f"{CBT.REFUND_CONFIRMED}:")
        )
        self.cbq_handler(
            self.open_order_menu,
            lambda c: c.data.startswith(f"{CBT.BACK_TO_ORDER_KB}:"),
        )
        self.cbq_handler(self.open_cp, lambda c: c.data == CBT.MAIN)
        self.cbq_handler(self.open_cp2, lambda c: c.data == CBT.MAIN2)
        self.cbq_handler(
            self.open_settings_section, lambda c: c.data.startswith(f"{CBT.CATEGORY}:")
        )
        self.cbq_handler(
            self.switch_param, lambda c: c.data.startswith(f"{CBT.SWITCH}:")
        )
        self.cbq_handler(
            self.switch_chat_notification,
            lambda c: c.data.startswith(f"{CBT.SWITCH_TG_NOTIFICATIONS}:"),
        )
        self.cbq_handler(
            self.power_off, lambda c: c.data.startswith(f"{CBT.SHUT_DOWN}:")
        )
        self.cbq_handler(
            self.cancel_power_off, lambda c: c.data == CBT.CANCEL_SHUTTING_DOWN
        )
        self.cbq_handler(self.cancel_action, lambda c: c.data == CBT.CLEAR_STATE)
        self.cbq_handler(
            self.send_old_mode_help_text, lambda c: c.data == CBT.OLD_MOD_HELP
        )
        self.cbq_handler(self.empty_callback, lambda c: c.data == CBT.EMPTY)
        self.cbq_handler(self.switch_lang, lambda c: c.data.startswith(f"{CBT.LANG}:"))

    def send_notification(
        self,
        text: str | None,
        keyboard: K | None = None,
        notification_type: str = utils.NotificationTypes.other,
        photo: bytes | None = None,
        pin: bool = False,
    ):
        if notification_type in DISABLED_NOTIFICATION_TYPES:
            return
        to_delete = []
        for chat_id in self.notification_settings:
            if not self.notification_recipient_allowed(chat_id):
                to_delete.append(chat_id)
                continue
            if not self.is_notification_enabled(chat_id, notification_type):
                continue
            if not self.deliver_separate_notification(
                chat_id, text, keyboard, notification_type, photo, pin
            ):
                to_delete.append(chat_id)
        for chat_id in to_delete:
            del self.notification_settings[chat_id]
        if to_delete:
            utils.save_notification_settings(self.notification_settings)

    def deliver_separate_notification(self, *args):
        navigation = getattr(self, "panel_navigation", None)
        scope = navigation.activate(None) if navigation else nullcontext()
        with scope:
            return self._deliver_notification(*args)

    def _deliver_notification(
        self, chat_id, text, keyboard, notification_type, photo, pin
    ):
        if not self.notification_recipient_allowed(chat_id):
            return False
        kwargs = {}
        if keyboard is not None:
            kwargs["reply_markup"] = keyboard
        try:
            if photo:
                msg = self.bot.send_photo(chat_id, photo, text, **kwargs)
            else:
                msg = self.bot.send_message(chat_id, text, **kwargs)
            if notification_type == utils.NotificationTypes.bot_start:
                self.init_messages.append((msg.chat.id, msg.id))
            if pin:
                self.bot.pin_chat_message(msg.chat.id, msg.id)
            return True
        except Exception as error:
            _module_state.logger.error(
                _module_state._("log_tg_notification_error", chat_id)
            )
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            return not self._is_unreachable_chat(error)

    @staticmethod
    def _is_unreachable_chat(error):
        return isinstance(error, ApiTelegramException) and (
            error.result.status_code == 403
            or (
                error.result.status_code == 400
                and error.result_json.get("description")
                in (
                    "Bad Request: group chat was upgraded to a supergroup chat",
                    "Bad Request: chat not found",
                )
            )
        )

    def add_command_to_menu(self, command: str, help_text: str) -> None:
        self.commands[command] = help_text

    def setup_commands(self):
        self.bot.delete_my_commands(language_code=REMOVED_LANGUAGE)
        for lang in (None, *_module_state.localizer.languages.keys()):
            commands = [
                BotCommand(command, _module_state._(label, language=lang))
                for command, label in self.commands.items()
            ]
            self.bot.set_my_commands(commands, language_code=lang)

    def init(self):
        self._TGBot__register_handlers()
        self.initialize_updates()
        from tg_bot.profile_branding import BotProfileBranding
        from tg_bot.constants.profile import PROFILE_SYNC_THREAD_NAME
        from threading import Thread

        Thread(
            target=BotProfileBranding(self.bot.token).synchronize,
            name=PROFILE_SYNC_THREAD_NAME,
            daemon=True,
        ).start()
        _module_state.logger.info(_module_state._("log_tg_initialized"))

    def run(self):
        self.send_notification(
            _module_state._("bot_started"),
            notification_type=utils.NotificationTypes.bot_start,
        )
        k_err = 0
        while True:
            try:
                _module_state.logger.info(
                    _module_state._("log_tg_started", self.bot.user.username)
                )
                self.bot.infinity_polling(logger_level=logging.DEBUG)
            except:
                k_err += 1
                _module_state.logger.error(
                    _module_state._("log_tg_update_error", k_err)
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                time.sleep(10)
