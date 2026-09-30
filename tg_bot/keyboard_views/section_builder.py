from telebot.types import InlineKeyboardMarkup

from tg_bot import CBT
from tg_bot.constants.section_layouts import STATE_DISABLED, STATE_ENABLED
from tg_bot.keyboard_views.styled_button import StyledButton


def setting_button(config, section, field, label, translate):
    enabled = config[section].getboolean(field)
    state = STATE_ENABLED if enabled else STATE_DISABLED
    return StyledButton(
        translate(label, state),
        callback_data=f"{CBT.SWITCH}:{section}:{field}",
    )


def settings_keyboard(config, section, rows, translate):
    keyboard = InlineKeyboardMarkup()
    for row in rows:
        keyboard.row(
            *(setting_button(config, section, *item, translate) for item in row)
        )
    return keyboard


def translated_button(translate, label, callback, style=None):
    return StyledButton(translate(label), callback_data=callback, style=style)


def section_back(keyboard, translate, callback):
    return keyboard.row(translated_button(translate, "gl_back", callback))
