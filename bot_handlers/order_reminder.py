from __future__ import annotations

from typing import TYPE_CHECKING

from FunPayAPI.updater.events import NewMessageEvent

if TYPE_CHECKING:
    from cardinal import Cardinal


def order_reminder_message_handler(c: Cardinal, e: NewMessageEvent):
    telegram = getattr(c, "telegram", None)
    service = getattr(telegram, "order_reminder", None) if telegram else None
    if service is not None:
        service.observe(e.message)
