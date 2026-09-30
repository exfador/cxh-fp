from copy import deepcopy

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


from tg_bot.constants.premium_emoji import (
    VARIATION_SELECTORS,
    ICON_FIELD,
    KEYBOARD_FIELD,
    TEXT_FIELD,
)


class PremiumKeyboard(InlineKeyboardMarkup):
    def __init__(self, payload, original_payload, row_width=3):
        keyboard = [
            [InlineKeyboardButton.de_json(button) for button in row]
            for row in payload[KEYBOARD_FIELD]
        ]
        super().__init__(keyboard=keyboard, row_width=row_width)
        self._payload = deepcopy(payload)
        self._original_payload = deepcopy(original_payload)

    def to_dict(self):
        return deepcopy(self._payload)

    def original_payload(self):
        return deepcopy(self._original_payload)


def decorate_button(button, prefixes, icons, enabled):
    if not enabled:
        button.pop(ICON_FIELD, None)
        return
    text = button.get(TEXT_FIELD, "")
    for prefix in prefixes:
        if not text.startswith(prefix):
            continue
        label = text[len(prefix) :].lstrip(VARIATION_SELECTORS).lstrip()
        if label:
            button[TEXT_FIELD] = label
            button[ICON_FIELD] = icons[prefix]
        return


def decorate_keyboard(markup, icons, enabled=True):
    if not isinstance(markup, InlineKeyboardMarkup):
        return markup
    original = (
        markup.original_payload()
        if isinstance(markup, PremiumKeyboard)
        else deepcopy(markup.to_dict())
    )
    payload = deepcopy(original)
    prefixes = sorted((prefix for prefix in icons if prefix), key=len, reverse=True)
    for row in payload[KEYBOARD_FIELD]:
        for button in row:
            decorate_button(button, prefixes, icons, enabled)
    return PremiumKeyboard(payload, original, row_width=markup.row_width)
