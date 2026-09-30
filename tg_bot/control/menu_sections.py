from locales.localizer import Localizer
from tg_bot.constants.menu import MENU_AUTOMATION_FIELDS, FUNPAY_PROFILE_URL
from tg_bot.keyboard_views.menu import (
    automation_keyboard,
    settings_keyboard,
    service_keyboard,
    menu_back,
    account_keyboard,
    restart_keyboard,
)
from tg_bot.menu_data import health_text, account_text
from telebot.types import InlineKeyboardMarkup
from Utils.cardinal_tools import restart_program


class MenuSections:
    def menu_automation(self, call, token, argument):
        translate = Localizer().translate
        lines = [translate("menu_automation_text")]
        for option, label in MENU_AUTOMATION_FIELDS:
            state = translate(
                "gl_on"
                if self.cardinal.MAIN_CFG["FunPay"].getboolean(option)
                else "gl_off"
            )
            lines.append(translate(label, state))
        self.menu_render(call, "\n".join(lines), automation_keyboard(token))

    def menu_settings(self, call, token, argument):
        self.menu_render(
            call, Localizer().translate("menu_settings_text"), settings_keyboard(token)
        )

    def menu_service(self, call, token, argument):
        self.menu_render(
            call, Localizer().translate("menu_service_text"), service_keyboard(token)
        )

    def menu_help(self, call, token, argument):
        self.menu_render(
            call,
            Localizer().translate("menu_help_text"),
            menu_back(InlineKeyboardMarkup(), token),
        )

    def menu_health(self, call, token, argument):
        self.menu_render(
            call,
            health_text(self.cardinal),
            menu_back(InlineKeyboardMarkup(), token, "service"),
        )

    def menu_profile(self, call, token, argument):
        identifier = str(self.cardinal.account.id or "")
        if not identifier.isascii() or not identifier.isdecimal():
            self.menu_render(
                call,
                Localizer().translate("menu_connecting"),
                menu_back(InlineKeyboardMarkup(), token),
            )
            return
        self.menu_render(
            call,
            account_text(self.cardinal),
            account_keyboard(token, FUNPAY_PROFILE_URL.format(identifier)),
        )

    def menu_restart(self, call, token, argument):
        self.menu_store.update(token, pending_restart=True)
        self.menu_render(
            call, Localizer().translate("menu_restart_text"), restart_keyboard(token)
        )

    def menu_confirm_restart(self, call, token, argument):
        if not self.menu_store.consume_restart(token):
            return
        self.menu_render(
            call, Localizer().translate("restarting"), InlineKeyboardMarkup()
        )
        restart_program()
