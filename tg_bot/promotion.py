from telebot.types import InlineKeyboardButton

from locales.localizer import Localizer
from tg_bot.keyboard_appearance import copy_keyboard
from tg_bot.constants.promotion import PLUGIN_STORE_LABEL, PLUGIN_STORE_URL


def plugin_store_keyboard(keyboard):
    result = copy_keyboard(keyboard.to_dict())
    if any(button.url == PLUGIN_STORE_URL for row in result.keyboard for button in row):
        return result
    return result.row(
        InlineKeyboardButton(
            Localizer().translate(PLUGIN_STORE_LABEL), url=PLUGIN_STORE_URL
        )
    )
