from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
import configparser
import json
import os.path
import unicodedata
from app.brand_policy import rebrand_message_signatures

from telebot.types import InlineKeyboardButton as B
from telebot.types import InlineKeyboardMarkup as K

import Utils.cardinal_tools
from app.constants.branding import (
    BRAND_ICON,
    BRAND_SIGNATURE,
    LEGACY_BRAND_SIGNATURES,
    PROJECT_NAME,
)
from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot.constants.message_formatting import (
    LEGACY_BRAND_ASCII,
    LEGACY_BRAND_MARKERS,
    MESSAGE_AUTHOR_FIELDS,
    MESSAGE_CODE_STYLE,
)
from tg_bot.message_formatting import message_author_header, message_body, message_is_ad

localizer = Localizer()
_ = localizer.translate


def parse_chat_id(value: str) -> int | str:
    if re.fullmatch(r"[0-9]+", value):
        return int(value)
    if re.fullmatch(r"users-[0-9]+-[0-9]+", value):
        return value
    raise ValueError("Invalid FunPay chat identifier")


class NotificationTypes:
    bot_start = "1"
    new_message = "2"
    command = "3"
    new_order = "4"
    order_confirmed = "5"
    review = "5r"
    lots_restore = "6"
    lots_deactivate = "7"
    delivery = "8"
    lots_raise = "9"
    other = "10"
    announcement = "11"
    ad = "12"
    critical = "13"
    important_announcement = "14"


def load_authorized_users() -> dict[int, dict[str, bool | None | str]]:
    if not os.path.exists("storage/cache/tg_authorized_users.json"):
        return dict()
    with open("storage/cache/tg_authorized_users.json", "r", encoding="utf-8") as f:
        data = f.read()
    data = json.loads(data)
    result = {}
    if isinstance(data, list):
        for i in data:
            result[i] = {}
        save_authorized_users(result)
    else:
        for k, v in data.items():
            result[int(k)] = v
    return result


def load_notification_settings() -> dict:
    if not os.path.exists("storage/cache/notifications.json"):
        return {}
    with open("storage/cache/notifications.json", "r", encoding="utf-8") as f:
        return json.loads(f.read())


def load_answer_templates() -> list[str]:
    if not os.path.exists("storage/cache/answer_templates.json"):
        return []
    with open("storage/cache/answer_templates.json", "r", encoding="utf-8") as f:
        return [rebrand_message_signatures(text) for text in json.loads(f.read())]


def save_authorized_users(users: dict[int, dict]) -> None:
    if not os.path.exists("storage/cache/"):
        os.makedirs("storage/cache/")
    with open("storage/cache/tg_authorized_users.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(users))


def save_notification_settings(settings: dict) -> None:
    if not os.path.exists("storage/cache/"):
        os.makedirs("storage/cache/")
    with open("storage/cache/notifications.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(settings))


def save_answer_templates(templates: list[str]) -> None:
    if not os.path.exists("storage/cache/"):
        os.makedirs("storage/cache")
    with open("storage/cache/answer_templates.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(templates))


def escape(text: str) -> str:
    escape_characters = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
    for char in escape_characters:
        text = text.replace(char, escape_characters[char])
    return text


def format_message_line(
    cardinal: Cardinal,
    msg,
    last: dict | None = None,
    *,
    force_show_author: bool = False,
    chat_url: bool = False,
    mono: bool = False,
    hide_watermark: bool = False,
    show_ads: bool = True,
    show_image_name: bool | None = None,
    system_message_style: str = MESSAGE_CODE_STYLE,
) -> str:
    if message_is_ad(msg) and not show_ads:
        return ""
    author = message_author_header(
        cardinal, msg, last or {}, force_show_author, chat_url
    )
    body = message_body(
        cardinal, msg, mono, hide_watermark, show_image_name, system_message_style
    )
    return f"{author}{body}"


def format_messages(cardinal: Cardinal, messages: list, **options) -> str:
    lines = []
    last: dict = {}
    for msg in messages:
        line = format_message_line(cardinal, msg, last, **options)
        if not line:
            continue
        lines.append(line)
        last = {field: getattr(msg, field) for field in MESSAGE_AUTHOR_FIELDS}
    return "\n\n".join(lines)


def has_brand_mark(watermark: str) -> bool:
    normalized = unicodedata.normalize("NFKD", watermark).casefold()
    simplified = normalized.encode("ascii", "ignore").decode("ascii")
    if any(keyword in simplified for keyword in LEGACY_BRAND_ASCII):
        return True
    markers = (
        *LEGACY_BRAND_MARKERS,
        *LEGACY_BRAND_SIGNATURES,
        PROJECT_NAME,
        BRAND_SIGNATURE,
        BRAND_ICON,
    )
    return any(
        unicodedata.normalize("NFKD", marker).casefold() in normalized
        for marker in markers
    )


def split_by_limit(list_of_str: list[str], limit: int = 4096):
    result = []
    current = ""
    for part in list_of_str:
        if len(current) + len(part) > limit:
            result.append(current)
            current = part
        else:
            current += part
    if current:
        result.append(current)
    return result


def bool_to_text(value: bool | int | str | None, on: str = "🟢", off: str = "🔴"):
    if value is not None and int(value):
        return on
    return off


def get_offset(element_index: int, max_elements_on_page: int) -> int:
    elements_amount = element_index + 1
    elements_on_page = elements_amount % max_elements_on_page
    elements_on_page = elements_on_page if elements_on_page else max_elements_on_page
    if not elements_amount - elements_on_page:
        return 0
    else:
        return element_index - elements_on_page + 1


def add_navigation_buttons(
    keyboard_obj: K,
    curr_offset: int,
    max_elements_on_page: int,
    elements_on_page: int,
    elements_amount: int,
    callback_text: str,
    extra: list | None = None,
) -> K:
    extra = ":" + ":".join(str(i) for i in extra) if extra else ""
    back, forward = (True, True)
    if curr_offset > 0:
        back_offset = (
            curr_offset - max_elements_on_page
            if curr_offset > max_elements_on_page
            else 0
        )
        back_cb = f"{callback_text}:{back_offset}{extra}"
        first_cb = f"{callback_text}:0{extra}"
    else:
        back, back_cb, first_cb = (False, CBT.EMPTY, CBT.EMPTY)
    if curr_offset + elements_on_page < elements_amount:
        forward_offset = curr_offset + elements_on_page
        last_page_offset = get_offset(elements_amount - 1, max_elements_on_page)
        forward_cb = f"{callback_text}:{forward_offset}{extra}"
        last_cb = f"{callback_text}:{last_page_offset}{extra}"
    else:
        forward, forward_cb, last_cb = (False, CBT.EMPTY, CBT.EMPTY)
    if back or forward:
        center_text = f"{curr_offset // max_elements_on_page + 1}/{math.ceil(elements_amount / max_elements_on_page)}"
        keyboard_obj.row(
            B("◀️◀️", callback_data=first_cb),
            B("◀️", callback_data=back_cb),
            B(center_text, callback_data=CBT.EMPTY),
            B("▶️", callback_data=forward_cb),
            B("▶️▶️", callback_data=last_cb),
        )
    return keyboard_obj


def generate_profile_text(cardinal: Cardinal) -> str:
    from tg_bot.menu_data import account_text

    return account_text(cardinal)


def generate_lot_info_text(lot_obj: configparser.SectionProxy) -> str:
    filename = lot_obj.get("productsFileName")
    file_text = _("lot_no_file")
    amount = "∞"
    if filename:
        path = os.path.join("storage/products", filename)
        amount = (
            Utils.cardinal_tools.count_products(path) if os.path.isfile(path) else 0
        )
        file_text = f"<code>{escape(filename)}</code>"
    return _(
        "lot_details_text",
        escape(lot_obj.name),
        escape(lot_obj["response"]),
        amount,
        file_text,
    )
