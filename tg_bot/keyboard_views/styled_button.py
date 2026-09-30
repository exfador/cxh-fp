from telebot.types import InlineKeyboardButton

from tg_bot.constants.button_styles import BUTTON_STYLES


class StyledButton(InlineKeyboardButton):
    def __init__(self, *args, style=None, **kwargs):
        if style is not None and style not in BUTTON_STYLES:
            raise ValueError("Unsupported Telegram button style")
        super().__init__(*args, **kwargs)
        self.style = style

    def to_dict(self):
        result = super().to_dict()
        if self.style is not None:
            result["style"] = self.style
        return result
