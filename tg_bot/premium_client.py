import inspect
from io import IOBase

import telebot
from telebot.apihelper import ApiTelegramException

from tg_bot.constants.premium_emoji import (
    ANIMATED_EMOJI,
    EMOJI_ERROR_MARKERS,
    HTML_PARSE_MODE,
    UPLOAD_FIELDS,
)
from tg_bot.premium_policy import OwnerPremiumPolicy
from tg_bot.premium_keyboard import decorate_keyboard
from tg_bot.premium_text import decorate_html
from tg_bot.link_previews import disable_link_previews
from tg_bot.keyboard_appearance import canonical_keyboard


def upload_positions(arguments):
    positions = []
    for field in UPLOAD_FIELDS:
        value = arguments.get(field)
        stream = value.file if isinstance(value, telebot.types.InputFile) else value
        if isinstance(stream, IOBase) and stream.seekable():
            positions.append((stream, stream.tell()))
    return positions


class PremiumTeleBot(telebot.TeleBot):
    def __init__(self, token, *args, emoji_policy=None, **kwargs):
        super().__init__(token, *args, **kwargs)
        self.emoji_policy = emoji_policy or OwnerPremiumPolicy(token)
        self.panel_navigation = None
        self.fallback_message_handler = None
        self.fallback_callback_handler = None

    @staticmethod
    def insert_before(handlers, fallback, handler_dict):
        if fallback is None or handler_dict is fallback:
            return False
        for index, existing in enumerate(handlers):
            if existing is fallback:
                handlers.insert(index, handler_dict)
                return True
        return False

    @staticmethod
    def move_last(handlers, handler_dict):
        if handler_dict in handlers:
            handlers.remove(handler_dict)
        handlers.append(handler_dict)
        return handler_dict

    def add_message_handler(self, handler_dict):
        if not self.insert_before(
            self.message_handlers, self.fallback_message_handler, handler_dict
        ):
            super().add_message_handler(handler_dict)

    def add_callback_query_handler(self, handler_dict):
        if not self.insert_before(
            self.callback_query_handlers, self.fallback_callback_handler, handler_dict
        ):
            super().add_callback_query_handler(handler_dict)

    def set_fallback_message_handler(self, handler_dict):
        self.fallback_message_handler = self.move_last(
            self.message_handlers, handler_dict
        )

    def set_fallback_callback_handler(self, handler_dict):
        self.fallback_callback_handler = self.move_last(
            self.callback_query_handlers, handler_dict
        )

    def send_message(self, *args, **kwargs):
        return self.ui_request(telebot.TeleBot.send_message, args, kwargs, "text")

    def edit_message_text(self, *args, **kwargs):
        return self.ui_request(telebot.TeleBot.edit_message_text, args, kwargs, "text")

    def send_photo(self, *args, **kwargs):
        return self.ui_request(telebot.TeleBot.send_photo, args, kwargs, "caption")

    def send_document(self, *args, **kwargs):
        return self.ui_request(telebot.TeleBot.send_document, args, kwargs, "caption")

    def edit_message_caption(self, *args, **kwargs):
        return self.ui_request(
            telebot.TeleBot.edit_message_caption, args, kwargs, "caption"
        )

    def edit_message_reply_markup(self, *args, **kwargs):
        return self.ui_request(
            telebot.TeleBot.edit_message_reply_markup, args, kwargs, None
        )

    def answer_callback_query(self, *args, **kwargs):
        bound = inspect.signature(telebot.TeleBot.answer_callback_query).bind(
            self, *args, **kwargs
        )
        navigation = self.panel_navigation
        if navigation is not None and not bound.arguments.get("text"):
            notice = navigation.unchanged_notice(bound.arguments["callback_query_id"])
            if notice:
                bound.arguments["text"] = notice
        return telebot.TeleBot.answer_callback_query(*bound.args, **bound.kwargs)

    def delete_message(self, *args, **kwargs):
        navigation = self.panel_navigation
        bound = inspect.signature(telebot.TeleBot.delete_message).bind(
            self, *args, **kwargs
        )
        if navigation and navigation.suppress_deletion(
            bound.arguments["chat_id"], bound.arguments["message_id"]
        ):
            return True
        return telebot.TeleBot.delete_message(*bound.args, **bound.kwargs)

    def ui_request(self, method, args, kwargs, text_field):
        if self.panel_navigation is not None:
            return self.panel_navigation.request(
                method, args, kwargs, text_field, self._ui_request
            )
        return self._ui_request(method, args, kwargs, text_field)

    def _ui_request(self, method, args, kwargs, text_field):
        bound = inspect.signature(method).bind(self, *args, **kwargs)
        disable_link_previews(bound)
        if "reply_markup" in bound.arguments:
            bound.arguments["reply_markup"] = canonical_keyboard(
                bound.arguments["reply_markup"]
            )
        original = dict(bound.arguments)
        if not self.can_decorate(bound.arguments):
            return method(*bound.args, **bound.kwargs)
        positions = upload_positions(original)
        self.decorate_arguments(bound.arguments, text_field)
        try:
            return method(*bound.args, **bound.kwargs)
        except ApiTelegramException as error:
            if error.error_code != 400 or not any(
                marker in error.description.casefold() for marker in EMOJI_ERROR_MARKERS
            ):
                raise
            self.emoji_policy.disable()
            for stream, position in positions:
                stream.seek(position)
            bound.arguments.clear()
            bound.arguments.update(original)
            return method(*bound.args, **bound.kwargs)

    def can_decorate(self, arguments):
        chat_id = arguments.get("chat_id")
        if isinstance(chat_id, str) and chat_id.isascii() and chat_id.isdecimal():
            chat_id = int(chat_id) if len(chat_id) <= 20 else None
        return (
            type(chat_id) is int
            and chat_id > 0
            and not arguments.get("inline_message_id")
            and self.emoji_policy.enabled()
        )

    def decorate_arguments(self, arguments, text_field):
        arguments["reply_markup"] = decorate_keyboard(
            arguments.get("reply_markup"), ANIMATED_EMOJI
        )
        mode = arguments.get("parse_mode") or self.parse_mode
        entities = arguments.get("entities") or arguments.get("caption_entities")
        if text_field and mode == HTML_PARSE_MODE and not entities:
            text = arguments.get(text_field)
            if isinstance(text, str):
                arguments[text_field] = decorate_html(text, ANIMATED_EMOJI)
