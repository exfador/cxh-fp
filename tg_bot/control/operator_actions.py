import logging
import secrets
import time
from html import escape
from types import SimpleNamespace

from requests.exceptions import RequestException
from telebot.apihelper import ApiTelegramException

from FunPayAPI.common.exceptions import AccountNotInitiatedError, RequestFailedError
from locales.localizer import Localizer
from app.constants.branding import DEFAULT_MESSAGE_SIGNATURE
from tg_bot import CBT
from tg_bot.constants.menu import MENU_NOT_MODIFIED
from tg_bot.constants.operator import (
    OPERATOR_ACTIONS,
    OPERATOR_CALLBACK_PARTS,
    OPERATOR_CONFIRMATION_BYTES,
    OPERATOR_CONFIRMATION_SECONDS,
    OPERATOR_CONFIRMATION_STATE,
    OPERATOR_FAILURE_LOG,
    OPERATOR_INPUT_HANDLERS,
    OPERATOR_LOGGER,
    OPERATOR_PREFIX,
)
from tg_bot.control.log_files import clear_logs_text
from tg_bot.keyboard_views.operator import (
    operator_images_keyboard,
    operator_logs_confirmation,
    operator_navigation,
    operator_system_keyboard,
    operator_watermark_keyboard,
)


class OperatorActions:
    def operator_callback(self, call):
        if not call.message or not self.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            self.bot.answer_callback_query(call.id)
            return
        parts = (call.data or "").split(":")
        if len(parts) not in OPERATOR_CALLBACK_PARTS or parts[0] != OPERATOR_PREFIX:
            self.bot.answer_callback_query(call.id)
            return
        action, argument = parts[1], parts[2] if len(parts) == 3 else None
        if action != "home":
            self.bot.answer_callback_query(call.id)
        self.operator_execute(call, action, argument)

    def operator_execute(self, call, action, argument):
        try:
            self.operator_dispatch(call, action, argument)
        except (
            OSError,
            ValueError,
            RuntimeError,
            RequestException,
            RequestFailedError,
            AccountNotInitiatedError,
            ApiTelegramException,
        ) as error:
            logging.getLogger(OPERATOR_LOGGER).warning(
                OPERATOR_FAILURE_LOG, action, type(error).__name__
            )
            self.operator_render(call, Localizer().translate("menu_action_error"))

    def operator_dispatch(self, call, action, argument):
        if action.startswith("bl_"):
            self.blocklist_callback(call, action, argument)
            return
        if action not in OPERATOR_ACTIONS:
            return
        if argument is not None and action != "logs_clear_confirm":
            return
        if action != "logs_clear_confirm":
            self.clear_state(call.message.chat.id, call.from_user.id)
        getattr(self, OPERATOR_ACTIONS[action])(call, argument)

    def operator_message(self, call):
        return SimpleNamespace(
            chat=call.message.chat, id=call.message.id, from_user=call.from_user
        )

    def operator_input(self, message):
        if not self.menu_user_allowed(message.from_user, message.chat):
            return
        state = self.get_state(message.chat.id, message.from_user.id)
        if not state or state["state"] not in OPERATOR_INPUT_HANDLERS:
            return
        if not isinstance(message.text, str) or message.text.startswith("/"):
            return
        section = state["data"].get("operator_return", "home")
        try:
            getattr(self, OPERATOR_INPUT_HANDLERS[state["state"]])(message)
        except OSError as error:
            logging.getLogger(OPERATOR_LOGGER).warning(
                OPERATOR_FAILURE_LOG, state["state"], type(error).__name__
            )
            self.bot.send_message(
                message.chat.id,
                Localizer().translate("menu_action_error"),
                reply_markup=operator_navigation(section),
            )
            return
        if self.get_state(message.chat.id, message.from_user.id) is None:
            self.operator_complete(message, section)

    def operator_complete(self, message, section="home"):
        if not self.menu_user_allowed(message.from_user, message.chat):
            return
        navigation = getattr(self, "panel_navigation", None)
        if navigation is not None and navigation.context.get() is not None:
            return
        self.bot.send_message(
            message.chat.id,
            Localizer().translate("operator_complete_text"),
            reply_markup=operator_navigation(section),
        )

    def operator_render(self, call, text, keyboard=None):
        try:
            self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.id,
                reply_markup=keyboard or operator_navigation(),
            )
        except ApiTelegramException as error:
            if MENU_NOT_MODIFIED in error.description.casefold():
                return
            raise

    def operator_home(self, call, argument=None):
        self.open_home_menu(call)

    def operator_session(self, call):
        token = self.menu_store.create(
            call.from_user.id, call.message.chat.id, call.message.id
        )
        call.menu_token = token
        call.menu_revision = 0
        return token

    def operator_service(self, call, argument=None):
        self.menu_service(call, self.operator_session(call), "-")

    def operator_images(self, call, argument=None):
        self.operator_render(
            call,
            Localizer().translate("operator_images_title"),
            operator_images_keyboard(),
        )

    def operator_prompt(self, call, text, state, section="service", keyboard=None):
        self.operator_render(call, text, keyboard or operator_navigation(section))
        self.set_state(
            call.message.chat.id,
            call.message.id,
            call.from_user.id,
            state,
            {"operator_return": section},
        )

    def operator_chat_image(self, call, argument=None):
        self.operator_prompt(
            call, Localizer().translate("send_img"), CBT.UPLOAD_CHAT_IMAGE, "images"
        )

    def operator_offer_image(self, call, argument=None):
        self.operator_prompt(
            call, Localizer().translate("send_img"), CBT.UPLOAD_OFFER_IMAGE, "images"
        )

    def operator_restore_backup(self, call, argument=None):
        self.operator_prompt(
            call, Localizer().translate("send_backup"), CBT.UPLOAD_BACKUP
        )

    def operator_delivery_test(self, call, argument=None):
        self.operator_prompt(
            call,
            Localizer().translate("create_test_ad_key"),
            CBT.MANUAL_AD_TEST,
            "home",
        )

    def operator_change_key(self, call, argument=None):
        self.operator_prompt(
            call,
            Localizer().translate("act_change_golden_key"),
            CBT.CHANGE_GOLDEN_KEY,
            "home",
        )

    def operator_watermark(self, call, argument=None):
        watermark = self.cardinal.MAIN_CFG["Other"]["watermark"]
        translate = Localizer().translate
        current = (
            f"\n<code>{escape(watermark)}</code>"
            if watermark
            else f" {translate('watermark_none')}"
        )
        text = translate("act_edit_watermark").format(current)
        self.operator_prompt(
            call, text, CBT.EDIT_WATERMARK, "home", operator_watermark_keyboard()
        )

    def operator_watermark_brand(self, call, argument=None):
        self.save_watermark(DEFAULT_MESSAGE_SIGNATURE)
        self.operator_watermark(call)

    def operator_watermark_clear(self, call, argument=None):
        self.save_watermark("")
        self.operator_watermark(call)

    def operator_logs_clear(self, call, argument=None):
        nonce = secrets.token_hex(OPERATOR_CONFIRMATION_BYTES)
        self.operator_render(
            call,
            Localizer().translate("operator_logs_clear_text"),
            operator_logs_confirmation(nonce),
        )
        self.set_state(
            call.message.chat.id,
            call.message.id,
            call.from_user.id,
            OPERATOR_CONFIRMATION_STATE,
            {"nonce": nonce, "created": time.monotonic()},
        )

    def operator_logs_confirmation_valid(self, call, argument):
        state = self.get_state(call.message.chat.id, call.from_user.id)
        if not state or state["state"] != OPERATOR_CONFIRMATION_STATE:
            return False
        data = state["data"]
        if state["mid"] != call.message.id or not isinstance(argument, str):
            return False
        if not argument.isascii() or len(argument) != OPERATOR_CONFIRMATION_BYTES * 2:
            return False
        if not secrets.compare_digest(data.get("nonce", ""), argument):
            return False
        age = time.monotonic() - data.get("created", 0)
        return 0 <= age <= OPERATOR_CONFIRMATION_SECONDS

    def operator_logs_clear_confirm(self, call, argument=None):
        with self.process_action_lock:
            if not self.operator_logs_confirmation_valid(call, argument):
                self.operator_service(call)
                return
            self.clear_state(call.message.chat.id, call.from_user.id)
            text = clear_logs_text()
        self.operator_render(call, text)

    def operator_system(self, call, argument=None):
        self.operator_render(
            call,
            self.system_info_text(call.message.chat.id),
            operator_system_keyboard(),
        )

    def operator_about(self, call, argument=None):
        self.operator_render(
            call, Localizer().translate("about", self.cardinal.VERSION)
        )

    def operator_refresh_profile(self, call, argument=None):
        self.cardinal.account.get()
        self.cardinal.balance = self.cardinal.get_balance()
        self.menu_profile(call, self.operator_session(call), "-", refreshed=True)
