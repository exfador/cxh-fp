from __future__ import annotations

import os
from logging import getLogger
from typing import TYPE_CHECKING

import requests
from telebot.types import InlineKeyboardButton as B
from telebot.types import InlineKeyboardMarkup as K

from tg_bot.utils import NotificationTypes

if TYPE_CHECKING:
    from cardinal import Cardinal

logger = getLogger("FPC.announcements")
REQUESTS_DELAY = 600
TAG_PATH = "storage/cache/announcement_tag.txt"
PHOTO_TIMEOUT = 30


def get_last_tag() -> str | None:
    if not os.path.exists(TAG_PATH):
        return None
    with open(TAG_PATH, "r", encoding="UTF-8") as f:
        return f.read()


LAST_TAG = get_last_tag()


def save_last_tag():
    if LAST_TAG is None:
        return
    os.makedirs(os.path.dirname(TAG_PATH), exist_ok=True)
    with open(TAG_PATH, "w", encoding="UTF-8") as f:
        f.write(LAST_TAG)


def get_announcement(ignore_last_tag: bool = False) -> dict | None:
    return None


def download_photo(url: str) -> bytes | None:
    try:
        response = requests.get(url, timeout=PHOTO_TIMEOUT)
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    return response.content


def get_notification_type(data: dict) -> str:
    types = {
        0: NotificationTypes.ad,
        1: NotificationTypes.announcement,
        2: NotificationTypes.important_announcement,
    }
    return types.get(data.get("type"), NotificationTypes.critical)


def get_photo(data: dict) -> bytes | None:
    photo = data.get("ph")
    return download_photo(str(photo)) if photo else None


def get_text(data: dict) -> str | None:
    text = data.get("text")
    return str(text) if text else None


def get_pin(data: dict) -> bool:
    return bool(data.get("pin"))


def get_keyboard(data: dict) -> K | None:
    rows = data.get("kb")
    if not rows:
        return None
    keyboard = K()
    try:
        for row in rows:
            keyboard.row(
                *(B(**{str(k): str(v) for k, v in item.items()}) for item in row)
            )
    except (TypeError, AttributeError, ValueError):
        return None
    return keyboard


def announcements_loop_iteration(crd: Cardinal, ignore_last_tag: bool = False):
    return None


def announcements_loop(crd: Cardinal):
    return None


def main(crd: Cardinal):
    return None
