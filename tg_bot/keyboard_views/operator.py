from telebot.types import InlineKeyboardMarkup

from locales.localizer import Localizer
from tg_bot.constants.operator import OPERATOR_PREFIX
from tg_bot.keyboard_views.styled_button import StyledButton


def operator_button(label, action, argument=None):
    callback = f"{OPERATOR_PREFIX}:{action}"
    if argument is not None:
        callback = f"{callback}:{argument}"
    return StyledButton(Localizer().translate(label), callback_data=callback)


def operator_navigation(section="service"):
    keyboard = InlineKeyboardMarkup()
    if section != "home":
        action = "bl_list" if section == "blacklist" else section
        keyboard.row(operator_button("gl_back", action))
    return keyboard.row(operator_button("menu_home_button", "home"))


def operator_images_keyboard():
    return (
        InlineKeyboardMarkup()
        .row(
            operator_button("operator_chat_image_button", "chat_image"),
            operator_button("operator_offer_image_button", "offer_image"),
        )
        .row(
            operator_button("gl_back", "service"),
            operator_button("menu_home_button", "home"),
        )
    )


def operator_logs_confirmation(nonce):
    return InlineKeyboardMarkup().row(
        operator_button(
            "operator_logs_clear_confirm_button", "logs_clear_confirm", nonce
        ),
        operator_button("gl_cancel", "service"),
    )


def operator_watermark_keyboard():
    keyboard = InlineKeyboardMarkup().row(
        operator_button("operator_watermark_brand", "watermark_brand"),
        operator_button("operator_watermark_clear", "watermark_clear"),
    )
    keyboard.keyboard.extend(operator_navigation("home").keyboard)
    return keyboard
