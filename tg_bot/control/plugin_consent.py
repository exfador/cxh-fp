import secrets

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot.constants.plugin_consent import (
    UPLOAD_CALLBACK_PARTS,
    UPLOAD_CHOICES,
    UPLOAD_CHOICE_NO,
    UPLOAD_CHOICE_YES,
    UPLOAD_CONSENT_PREFIX,
    UPLOAD_CONSENT_STATE,
    UPLOAD_CONSENT_TOKEN_BYTES,
)
from tg_bot.control.plugin_upload import upload_keyboard


def consent_keyboard(nonce):
    translate = Localizer().translate
    return InlineKeyboardMarkup().row(
        InlineKeyboardButton(
            translate("gl_yes"),
            callback_data=f"{UPLOAD_CONSENT_PREFIX}:{nonce}:{UPLOAD_CHOICE_YES}",
        ),
        InlineKeyboardButton(
            translate("gl_no"),
            callback_data=f"{UPLOAD_CONSENT_PREFIX}:{nonce}:{UPLOAD_CHOICE_NO}",
        ),
    )


class PluginUploadConsent:
    def __init__(self, controller, return_to_plugins):
        self.controller = controller
        self.return_to_plugins = return_to_plugins

    def request(self, call):
        if not call.message or not self.controller.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            return
        offset = int(call.data.split(":")[1])
        nonce = secrets.token_hex(UPLOAD_CONSENT_TOKEN_BYTES)
        self.show_confirmation(call, offset, nonce)

    def show_confirmation(self, call, offset, nonce):
        self.controller.clear_state(call.message.chat.id, call.from_user.id)
        self.controller.bot.edit_message_text(
            Localizer().translate("plugin_upload_confirmation"),
            call.message.chat.id,
            call.message.id,
            reply_markup=consent_keyboard(nonce),
        )
        self.controller.set_state(
            call.message.chat.id,
            call.message.id,
            call.from_user.id,
            UPLOAD_CONSENT_STATE,
            {"offset": offset, "nonce": nonce},
        )
        self.controller.bot.answer_callback_query(call.id)

    def confirmed_state(self, call):
        if not call.message or not self.controller.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            return None
        parts = call.data.split(":")
        if (
            len(parts) != UPLOAD_CALLBACK_PARTS
            or parts[0] != UPLOAD_CONSENT_PREFIX
            or parts[2] not in UPLOAD_CHOICES
            or not parts[1].isascii()
        ):
            return None
        state = self.controller.get_state(call.message.chat.id, call.from_user.id)
        if not state or state["state"] != UPLOAD_CONSENT_STATE:
            return None
        if state["mid"] != call.message.id or not secrets.compare_digest(
            state["data"]["nonce"], parts[1]
        ):
            return None
        return state

    def decide(self, call):
        state = self.confirmed_state(call)
        if state is None:
            self.controller.bot.answer_callback_query(
                call.id, Localizer().translate("plugin_upload_confirmation_expired")
            )
            return
        self.controller.clear_state(call.message.chat.id, call.from_user.id)
        offset = state["data"]["offset"]
        if call.data.split(":")[2] == UPLOAD_CHOICE_NO:
            self.cancel(call, offset)
            return
        self.accept(call, offset)

    def accept(self, call, offset):
        self.controller.bot.edit_message_text(
            Localizer().translate("pl_new"),
            call.message.chat.id,
            call.message.id,
            reply_markup=upload_keyboard(offset),
        )
        self.controller.set_state(
            call.message.chat.id,
            call.message.id,
            call.from_user.id,
            CBT.UPLOAD_PLUGIN,
            {"offset": offset, "confirmed": True},
        )
        self.controller.bot.answer_callback_query(call.id)

    def cancel(self, call, offset):
        navigation = getattr(self.controller, "panel_navigation", None)
        key = (call.from_user.id, call.message.chat.id, call.message.id)
        if navigation and navigation.history.contains(*key):
            call.data = navigation.history.current(*key).back_callback
            navigation.go_back(call)
            return
        call.data = f"{CBT.PLUGINS_LIST}:{offset}"
        self.return_to_plugins(call)
