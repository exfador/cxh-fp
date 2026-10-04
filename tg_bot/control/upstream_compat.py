import logging

from telebot.types import InlineKeyboardMarkup, Message

from app.constants import update_runtime as settings
from locales.localizer import Localizer
from tg_bot import keyboards
from tg_bot.control.updates import update_text
from tg_bot.profile_branding import BotProfileBranding


class UpstreamCompat:
    def edit_bot(self):
        BotProfileBranding(self.bot.token).synchronize()

    def check_updates(self, m: Message):
        text, keyboard = self.update_status()
        self.bot.send_message(m.chat.id, text, reply_markup=keyboard)

    def update(self, m: Message):
        self.check_updates(m)

    def update_status(self):
        service = getattr(self, "update_service", None)
        if service is None or not service.public_key:
            return update_text("disabled"), None
        try:
            service.check()
        except Exception as error:
            logging.getLogger(settings.UPDATE_LOGGER).warning(
                "Manual release check failed: %s", type(error).__name__
            )
            return update_text("failed"), None
        if not service.pending:
            return update_text("latest"), None
        keyboard = InlineKeyboardMarkup().row(self.update_install_button(service.token))
        return update_text("available", version=service.pending[0]["version"]), keyboard

    def send_announcements_kb(self, m: Message):
        self.bot.send_message(
            m.chat.id,
            Localizer().translate("desc_an"),
            reply_markup=keyboards.announcements_settings(self.cardinal, m.chat.id),
        )
