from copy import deepcopy

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from tg_bot.constants.keyboard_appearance import APPEARANCE_FIELDS
from tg_bot.constants.premium_emoji import (
    ANIMATED_EMOJI,
    ICON_FIELD,
    KEYBOARD_FIELD,
    TEXT_FIELD,
)


class AppearanceButton(InlineKeyboardButton):
    def __init__(self, **arguments):
        appearance = {
            field: arguments.pop(field)
            for field in APPEARANCE_FIELDS
            if field in arguments
        }
        super().__init__(**arguments)
        self.appearance = appearance

    def to_dict(self):
        return {**super().to_dict(), **self.appearance}


def keyboard_payload(markup):
    if hasattr(markup, "original_payload"):
        return markup.original_payload()
    return deepcopy(markup.to_dict() if hasattr(markup, "to_dict") else markup)


def copy_keyboard(markup):
    payload = keyboard_payload(markup)
    if not isinstance(payload, dict) or KEYBOARD_FIELD not in payload:
        return markup
    return InlineKeyboardMarkup(
        keyboard=[
            [AppearanceButton.de_json(button) for button in row]
            for row in payload[KEYBOARD_FIELD]
        ]
    )


def restore_button_emoji(button):
    icon = button.pop(ICON_FIELD, None)
    prefix = next(
        (emoji for emoji, identifier in ANIMATED_EMOJI.items() if identifier == icon),
        None,
    )
    text = button.get(TEXT_FIELD, "")
    if prefix and not text.startswith(prefix):
        button[TEXT_FIELD] = f"{prefix} {text}"


def canonical_keyboard(markup):
    payload = keyboard_payload(markup)
    if not isinstance(payload, dict) or KEYBOARD_FIELD not in payload:
        return markup
    for row in payload[KEYBOARD_FIELD]:
        for button in row:
            restore_button_emoji(button)
    return copy_keyboard(payload)


def incoming_keyboard(message):
    payload = getattr(message, "json", None)
    markup = payload.get("reply_markup") if isinstance(payload, dict) else None
    return canonical_keyboard(markup or getattr(message, "reply_markup", None))
