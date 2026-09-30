from __future__ import annotations
import time
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    pass
from FunPayAPI.updater.events import *
import FunPayAPI.updater.runner as _module_state


class OrderEventProcessing:
    def mark_as_by_bot(self, chat_id: int, message_id: int):
        if self.by_bot_ids.get(chat_id) is None:
            self.by_bot_ids[chat_id] = [message_id]
        else:
            self.by_bot_ids[chat_id].append(message_id)

    def listen(
        self, requests_delay: int | float = 6.0, ignore_exceptions: bool = True
    ) -> Generator[
        InitialChatEvent
        | ChatsListChangedEvent
        | LastChatMessageChangedEvent
        | NewMessageEvent
        | InitialOrderEvent
        | OrdersListChangedEvent
        | NewOrderEvent
        | OrderStatusChangedEvent
    ]:
        while True:
            start_time = time.time()
            try:
                if not (self._Runner__orders_counters and self._Runner__chat_bookmarks):
                    updates_objects = self.get_updates()["objects"]
                    is_request_made = True
                else:
                    updates_objects = [self._Runner__orders_counters]
                    chat_bookmarks = self._Runner__chat_bookmarks[::-1]
                    chat_ids = set()
                    for cb in chat_bookmarks:
                        cb_ids = set(cb["data"]["order"])
                        if chat_ids.issuperset(cb_ids):
                            continue
                        chat_ids.update(cb_ids)
                        updates_objects.append(cb)
                    is_request_made = False
                self._Runner__orders_counters = None
                self._Runner__chat_bookmarks = []
                events = self.parse_updates(updates_objects)
                if is_request_made and (not events):
                    self._Runner__chat_nodes = {}
                for event in events:
                    yield event
            except Exception as e:
                if not ignore_exceptions:
                    raise e
                else:
                    _module_state.logger.error(
                        "Произошла ошибка при получении событий. (ничего страшного, если это сообщение появляется нечасто)."
                    )
                    _module_state.logger.debug("TRACEBACK", exc_info=True)
            iteration_time = time.time() - start_time
            if time.time() - self.account.last_429_err_time > 60:
                rt = requests_delay - iteration_time
                if rt > 0:
                    time.sleep(rt)
            else:
                time.sleep(requests_delay)
