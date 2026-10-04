from html import escape
from urllib.parse import quote

from telebot.types import InlineKeyboardButton as B
from telebot.types import InlineKeyboardMarkup as K

from FunPayAPI.common.enums import MessageTypes
from locales.localizer import Localizer
from tg_bot import utils
from tg_bot.constants.chat_sync import (
    CHAT_SYNC_GROUP_PREFIX,
    CHAT_SYNC_TEMPLATE_LABEL,
    CHAT_SYNC_TEXT_LIMIT,
    CHAT_SYNC_TOPIC_NAME_LIMIT,
    FUNPAY_PURCHASES_BY_SELLER,
    FUNPAY_SALES_BY_BUYER,
)
from tg_bot.constants.message_formatting import FUNPAY_CHAT_LINK, MESSAGE_EMPHASIS_STYLE
from tg_bot.message_formatting import message_author_header

PAID_TYPES = frozenset({MessageTypes.ORDER_PURCHASED})
CLOSED_TYPES = frozenset(
    {MessageTypes.ORDER_CONFIRMED, MessageTypes.ORDER_CONFIRMED_BY_ADMIN}
)
REFUND_TYPES = frozenset(
    {MessageTypes.REFUND, MessageTypes.PARTIAL_REFUND, MessageTypes.REFUND_BY_ADMIN}
)


def translate(key, *args):
    return Localizer().translate(key, *args)


def topic_title(name, chat_id):
    title = (name or "").strip() or f"FunPay {chat_id}"
    return title[:CHAT_SYNC_TOPIC_NAME_LIMIT]


def split_text(text, limit=CHAT_SYNC_TEXT_LIMIT):
    parts, current = [], ""
    for block in text.split("\n\n"):
        piece = f"\n\n{block}" if current else block
        if len(current) + len(piece) <= limit:
            current += piece
            continue
        if current:
            parts.append(current)
        while len(block) > limit:
            parts.append(block[:limit])
            block = block[limit:]
        current = block
    if current.strip():
        parts.append(current)
    return parts


def format_block(cardinal, messages, hide_watermark):
    return utils.format_messages(
        cardinal,
        messages,
        hide_watermark=hide_watermark,
        system_message_style=MESSAGE_EMPHASIS_STYLE,
    )


def render_parts(cardinal, messages, hide_watermark):
    parts, block = [], []

    def flush():
        if block:
            text = format_block(cardinal, block, hide_watermark)
            parts.extend(("text", chunk) for chunk in split_text(text))
            block.clear()

    for message in messages:
        if not message.text and message.image_link:
            flush()
            caption = message_author_header(cardinal, message, {}, True, False)
            parts.append(("photo", message.image_link, caption.strip()))
        elif message.text:
            block.append(message)
    flush()
    return parts


def photo_fallback(part):
    link = f'<a href="{escape(part[1], quote=True)}">{escape(translate("photo"))}</a>'
    return f"{part[2]}\n{link}" if part[2] else link


def message_icon(message):
    if message.type in PAID_TYPES and not message.i_am_buyer:
        return "paid"
    if message.type in CLOSED_TYPES:
        return "closed"
    if message.type in REFUND_TYPES:
        return "refund"
    if message.is_arbitration or message.is_moderation:
        return "support"
    return None


def stack_icon(messages):
    for message in reversed(messages):
        icon = message_icon(message)
        if icon:
            return icon
    return None


def header_text(name, chat_id):
    title = escape(name or str(chat_id))
    encoded = quote(name or "")
    return translate(
        "cs_topic_header",
        title,
        FUNPAY_CHAT_LINK.format(chat_id),
        FUNPAY_SALES_BY_BUYER.format(encoded),
        FUNPAY_PURCHASES_BY_SELLER.format(encoded),
    )


def header_keyboard(chat_id):
    prefix = CHAT_SYNC_GROUP_PREFIX
    return (
        K()
        .row(B(translate("cs_open_chat"), url=FUNPAY_CHAT_LINK.format(chat_id)))
        .row(
            B(translate("cs_history_button"), callback_data=f"{prefix}:h:{chat_id}"),
            B(translate("cs_templates_button"), callback_data=f"{prefix}:t:{chat_id}"),
        )
    )


def template_label(index, template):
    text = " ".join(template.split())
    if len(text) > CHAT_SYNC_TEMPLATE_LABEL:
        text = text[: CHAT_SYNC_TEMPLATE_LABEL - 1] + "…"
    return f"{index + 1}. {text}"


def templates_keyboard(chat_id, templates):
    prefix = CHAT_SYNC_GROUP_PREFIX
    keyboard = K()
    for index, template in enumerate(templates):
        keyboard.row(
            B(
                template_label(index, template),
                callback_data=f"{prefix}:s:{chat_id}:{index}",
            )
        )
    return keyboard.row(B(translate("cs_close"), callback_data=f"{prefix}:x:{chat_id}"))
