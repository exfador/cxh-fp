from html import escape

from app.constants.branding import BRAND_ICON, BRAND_SIGNATURE
from app.brand_policy import message_signature_body
from locales.localizer import Localizer
from tg_bot.constants.message_formatting import (
    FUNPAY_AD_AUTHOR_ID,
    FUNPAY_CHAT_LINK,
    FUNPAY_SYSTEM_AUTHOR_ID,
    MESSAGE_AUTHOR_FIELDS,
    MESSAGE_EMPHASIS_STYLE,
)


def message_is_ad(message):
    return (
        message.author_id == FUNPAY_AD_AUTHOR_ID
        and message.interlocutor_id != FUNPAY_AD_AUTHOR_ID
    )


def message_author_matches(message, last):
    return all(
        getattr(message, field) == last.get(field) for field in MESSAGE_AUTHOR_FIELDS
    )


def message_author_name(message, chat_url):
    name = escape(message.author or "")
    if not chat_url:
        return name
    return (
        f"<a href='{FUNPAY_CHAT_LINK.format(escape(str(message.chat_id)))}'>{name}</a>"
    )


def message_customer_author(cardinal, message, name):
    badge = escape(str(message.badge or ""))
    if message.is_autoreply:
        return f"🛍️ {name} ({badge})"
    if message.author in cardinal.blacklist:
        return f"🚷 {name}"
    if message.by_bot:
        return f"{BRAND_ICON} {name}"
    if message.by_vertex:
        return f"🐺 {name}"
    return f"👤 {name}"


def message_own_author(message):
    translate = Localizer().translate
    if message.is_autoreply:
        badge = escape(str(message.badge or ""))
        return f"📦 {translate('you')} ({badge})"
    if message.by_bot:
        return BRAND_SIGNATURE
    return f"🫵 {translate('you')}"


def message_author_label(cardinal, message, chat_url):
    name = message_author_name(message, chat_url)
    if message.author_id == cardinal.account.id:
        return message_own_author(message)
    if message.author_id == FUNPAY_SYSTEM_AUTHOR_ID:
        return f"🔵 {name}"
    if message.is_employee:
        icon = "📣" if message_is_ad(message) else "🆘"
        return f"{icon} {name} ({escape(str(message.badge or ''))})"
    if message.author == message.chat_name:
        return message_customer_author(cardinal, message, name)
    return f"🆘 {name} ({Localizer().translate('support')})"


def message_author_header(cardinal, message, last, force_show_author, chat_url):
    if not force_show_author and message_author_matches(message, last):
        return ""
    return f"<b>{message_author_label(cardinal, message, chat_url)}</b>\n"


def message_text_body(cardinal, message, mono, hide_watermark, system_message_style):
    if (
        message.author_id == FUNPAY_SYSTEM_AUTHOR_ID
        and system_message_style == MESSAGE_EMPHASIS_STYLE
    ):
        return f"<b><i>{escape(message.text)}</i></b>"
    text = message.text
    watermark = cardinal.MAIN_CFG["Other"].get("watermark", "")
    own_bot = message.author_id == cardinal.account.id and message.by_bot
    hidden = False
    if own_bot:
        text, hidden = message_signature_body(text, watermark, hide_watermark)
    body = escape(text)
    if mono:
        body = f"<code>{body}</code>"
    return f"<tg-spoiler>{BRAND_ICON}</tg-spoiler>{body}" if hidden else body


def message_image_body(cardinal, message, show_image_name):
    own_bot = message.author_id == cardinal.account.id and message.by_bot
    show_name = cardinal.show_image_name if show_image_name is None else show_image_name
    name = message.image_name if show_name and not own_bot else None
    label = escape(name or Localizer().translate("photo"))
    return f'<a href="{escape(message.image_link, quote=True)}">{label}</a>'


def message_body(
    cardinal, message, mono, hide_watermark, show_image_name, system_message_style
):
    if message.text:
        return message_text_body(
            cardinal, message, mono, hide_watermark, system_message_style
        )
    if message.image_link:
        return message_image_body(cardinal, message, show_image_name)
    return ""
