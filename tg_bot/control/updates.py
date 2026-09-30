import logging
from pathlib import Path
from threading import Thread

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import update_runtime as settings
from app.constants.runtime import VERSION
from app.updates.service import UpdateService
from app.updates.constants import MANAGED_RUNTIME_ERROR
from locales.localizer import Localizer
from tg_bot.constants.update_ui import UPDATE_TEXTS
from tg_bot.keyboard_views.menu import menu_back, menu_button
from tg_bot import CBT
from telebot.apihelper import ApiTelegramException
from tg_bot.constants.menu import MENU_NOT_MODIFIED


def update_text(key, **values):
    language = Localizer().current_language
    return UPDATE_TEXTS.get(language, UPDATE_TEXTS["ru"])[key].format(**values)


def update_home_keyboard():
    return InlineKeyboardMarkup().row(
        InlineKeyboardButton(
            Localizer().translate("menu_home_button"), callback_data=CBT.MAIN
        )
    )


class UpdatePanel:
    def initialize_updates(self):
        self.update_service = UpdateService(
            self, Path.cwd(), settings.UPDATE_REPOSITORY, settings.UPDATE_PUBLIC_KEY
        )
        self.cbq_handler(
            self.update_callback,
            lambda call: (call.data or "").startswith(
                settings.UPDATE_CALLBACK_PREFIX + ":"
            ),
        )
        self.update_service.start()

    def menu_updates(self, call, token, argument):
        service = getattr(self, "update_service", None)
        if service is None or not service.public_key:
            return self.menu_render(
                call,
                update_text("disabled"),
                menu_back(InlineKeyboardMarkup(), token, "service"),
            )
        text = update_text("title") + "\n\n" + update_text("current", version=VERSION)
        keyboard = InlineKeyboardMarkup().row(
            menu_button("menu_check_updates_button", token, "check_updates")
        )
        if service.pending:
            text += "\n\n" + update_text(
                "available", version=service.pending[0]["version"]
            )
            keyboard.row(self.update_install_button(service.token))
        self.menu_render(call, text, menu_back(keyboard, token, "service"))

    def menu_check_updates(self, call, token, argument):
        self.menu_render(
            call,
            update_text("checking"),
            menu_back(InlineKeyboardMarkup(), token, "service"),
        )
        Thread(
            target=self.check_updates_background, args=(call, token), daemon=True
        ).start()

    def check_updates_background(self, call, token):
        try:
            result = self.update_service.check()
            if result:
                return self.menu_updates(call, token, "-")
            self.menu_render(
                call,
                update_text("latest"),
                menu_back(InlineKeyboardMarkup(), token, "service"),
            )
        except Exception as error:
            logging.getLogger(settings.UPDATE_LOGGER).warning(
                "Manual release check failed: %s", type(error).__name__
            )
            self.menu_render(
                call,
                update_text("failed"),
                menu_back(InlineKeyboardMarkup(), token, "service"),
            )

    def update_install_button(self, token):
        return InlineKeyboardButton(
            update_text("install"),
            callback_data=f"{settings.UPDATE_CALLBACK_PREFIX}:{token}",
        )

    def update_release_notification(self, user_id, version, token):
        if not self.notification_recipient_allowed(user_id):
            return False
        self.bot.send_message(
            user_id,
            update_text("available", version=version),
            reply_markup=InlineKeyboardMarkup().row(self.update_install_button(token)),
            disable_web_page_preview=True,
        )
        return True

    def update_callback(self, call):
        self.bot.answer_callback_query(call.id)
        if not call.message or not self.menu_user_allowed(
            call.from_user, call.message.chat
        ):
            return
        Thread(target=self.install_update_background, args=(call,), daemon=True).start()

    def install_update_background(self, call):
        try:
            self.update_service.install(call, call.data.split(":", 1)[1])
        except Exception as error:
            logging.getLogger(settings.UPDATE_LOGGER).warning(
                "Release installation rejected: %s", type(error).__name__
            )
            key = "expired" if isinstance(error, PermissionError) else "failed"
            if isinstance(error, BlockingIOError):
                key = "busy"
            if isinstance(error, ValueError) and "Dependency changes" in str(error):
                key = "dependencies"
            if isinstance(error, ValueError) and str(error) == MANAGED_RUNTIME_ERROR:
                key = "managed"
            self.update_progress(call, key)

    def update_result_notification(self, request):
        user_id = request["recipient"]
        if (
            type(user_id) is not int
            or user_id <= 0
            or not self.notification_recipient_allowed(user_id)
        ):
            return False
        text = update_text(request["status"], version=request["version"])
        keyboard = update_home_keyboard()
        try:
            self.bot.edit_message_text(
                text,
                user_id,
                request["message_id"],
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except ApiTelegramException as error:
            if MENU_NOT_MODIFIED in error.description.casefold():
                return True
            if not self.notification_recipient_allowed(user_id):
                return False
            self.bot.send_message(
                user_id, text, reply_markup=keyboard, disable_web_page_preview=True
            )
        return True

    def update_progress(self, call, key):
        if not self.menu_user_allowed(call.from_user, call.message.chat):
            return
        keyboard = update_home_keyboard()
        self.bot.edit_message_text(
            update_text(key),
            call.message.chat.id,
            call.message.id,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
