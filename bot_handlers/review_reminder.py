from __future__ import annotations

from typing import TYPE_CHECKING

from FunPayAPI.updater.events import (
    LastChatMessageChangedEvent,
    NewMessageEvent,
    OrderStatusChangedEvent,
)

if TYPE_CHECKING:
    from cardinal import Cardinal


def review_reminder_of(c: Cardinal):
    telegram = getattr(c, "telegram", None)
    return getattr(telegram, "review_reminder", None) if telegram else None


def review_reminder_status_handler(c: Cardinal, e: OrderStatusChangedEvent):
    service = review_reminder_of(c)
    if service is not None:
        service.confirmed(e.order)


def review_reminder_message_handler(c: Cardinal, e: NewMessageEvent):
    service = review_reminder_of(c)
    if service is not None:
        service.observe(e.message)


def review_reminder_chat_handler(c: Cardinal, e: LastChatMessageChangedEvent):
    service = review_reminder_of(c)
    if service is not None and c.old_mode_enabled:
        service.observe(e.chat)
