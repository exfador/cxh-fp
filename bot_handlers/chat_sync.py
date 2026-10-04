from __future__ import annotations

from typing import TYPE_CHECKING

from FunPayAPI.updater.events import InitialChatEvent, NewMessageEvent

if TYPE_CHECKING:
    from cardinal import Cardinal


def chat_sync_service(c: Cardinal):
    telegram = getattr(c, "telegram", None)
    return getattr(telegram, "chat_sync", None) if telegram else None


def chat_sync_message_handler(c: Cardinal, e: NewMessageEvent):
    service = chat_sync_service(c)
    if service is not None:
        service.accept(e)


def chat_sync_initial_handler(c: Cardinal, e: InitialChatEvent):
    service = chat_sync_service(c)
    if service is not None:
        service.accept_initial(e)
