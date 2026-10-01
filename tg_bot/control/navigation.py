import logging

from telebot.apihelper import ApiTelegramException

from locales.localizer import Localizer
from tg_bot.constants.menu import (
    MENU_PREFIX,
    MENU_CALLBACK_PARTS,
    MENU_ACTION_HANDLERS,
    MENU_PRIVATE_CHAT,
    MENU_FAILURE_LOG,
    MENU_LOGGER,
    MENU_NOT_MODIFIED,
)
from tg_bot import static_keyboards
from tg_bot.keyboard_views.menu import home_keyboard
from tg_bot.menu_data import home_text


class MenuNavigation:
    def menu_user_allowed(self, user, chat):
        return (
            user is not None
            and user.id in self.authorized_users
            and chat.type == MENU_PRIVATE_CHAT
            and chat.id == user.id
        )

    def send_home_menu(self, message):
        if not self.menu_user_allowed(message.from_user, message.chat):
            return
        self.clear_state(message.chat.id, message.from_user.id)
        token = self.menu_store.create(message.from_user.id, message.chat.id, 0)
        text = home_text(self.cardinal)
        keyboard = home_keyboard(token)
        sent = self.bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard,
        )
        self.menu_store.update(token, message_id=sent.id)
        navigation = getattr(self, "panel_navigation", None)
        if navigation is not None:
            navigation.history.begin(
                message.from_user.id, message.chat.id, sent.id, text, keyboard
            )

    def open_home_menu(self, call):
        if not call.message or not self.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            return
        self.clear_state(call.message.chat.id, call.from_user.id)
        token = self.menu_store.create(
            call.from_user.id, call.message.chat.id, call.message.id
        )
        call.menu_token = token
        call.menu_revision = 0
        self.menu_home(call, token, "-")
        self.bot.answer_callback_query(call.id)

    def menu_callback(self, call):
        if not call.message or not self.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            self.bot.answer_callback_query(call.id)
            return
        parts = (call.data or "").split(":")
        if len(parts) != MENU_CALLBACK_PARTS or parts[0] != MENU_PREFIX:
            return
        _, token, action, argument = parts
        session = self.menu_store.get(
            token, call.from_user.id, call.message.chat.id, call.message.id
        )
        if session is None or action not in MENU_ACTION_HANDLERS:
            self.bot.answer_callback_query(
                call.id, Localizer().translate("menu_expired")
            )
            return
        self.bot.answer_callback_query(call.id)
        if action != "confirm_restart":
            self.menu_store.update(token, pending_restart=False)
        self.clear_state(call.message.chat.id, call.from_user.id)
        self.menu_dispatch(call, token, action, argument)

    def menu_dispatch(self, call, token, action, argument):
        call.menu_token = token
        call.menu_revision = self.menu_store.advance(token)
        if call.menu_revision is None:
            return
        try:
            getattr(self, MENU_ACTION_HANDLERS[action])(call, token, argument)
        except Exception as error:
            logging.getLogger(MENU_LOGGER).warning(
                MENU_FAILURE_LOG, action, type(error).__name__
            )
            self.menu_render(
                call, Localizer().translate("menu_action_error"), home_keyboard(token)
            )

    def menu_render(self, call, text, keyboard):
        if not self.menu_response_is_current(call):
            return
        try:
            self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.id,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except ApiTelegramException as error:
            if MENU_NOT_MODIFIED in error.description.casefold():
                return
            raise

    def menu_response_is_current(self, call):
        if not self.menu_user_allowed(call.from_user, call.message.chat):
            return False
        token = getattr(call, "menu_token", None)
        if token is None:
            return True
        session = self.menu_store.get(
            token, call.from_user.id, call.message.chat.id, call.message.id
        )
        return session is not None and session.revision == call.menu_revision

    def menu_home(self, call, token, argument):
        self.clear_state(call.message.chat.id, call.from_user.id)
        self.menu_render(call, home_text(self.cardinal), home_keyboard(token))

    def open_more_settings(self, call):
        if not call.message or not self.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            return
        self.clear_state(call.message.chat.id, call.from_user.id)
        call.menu_token = self.menu_store.create(
            call.from_user.id, call.message.chat.id, call.message.id
        )
        call.menu_revision = 0
        self.menu_render(
            call,
            Localizer().translate("menu_more_settings_text"),
            static_keyboards.SETTINGS_SECTIONS_2(),
        )
        self.bot.answer_callback_query(call.id)
