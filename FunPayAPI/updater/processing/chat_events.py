from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
from bs4 import BeautifulSoup
from FunPayAPI.common import exceptions
from FunPayAPI.common.utils import strip_invisible_suffix
from FunPayAPI.updater.events import *
import FunPayAPI.updater.runner as _module_state


class ChatEventProcessing:
    def parse_chat_updates(
        self, obj
    ) -> list[
        InitialChatEvent
        | ChatsListChangedEvent
        | LastChatMessageChangedEvent
        | NewMessageEvent
    ]:
        events, lcmc_events = ([], [])
        self._Runner__last_msg_event_tag = obj.get("tag")
        parser = BeautifulSoup(obj["data"]["html"], "lxml")
        chats = parser.find_all("a", {"class": "contact-item"})
        for chat in chats:
            chat_id = int(chat["data-id"])
            if not (
                last_msg_text := chat.find("div", {"class": "contact-item-message"})
            ):
                continue
            last_msg_text = last_msg_text.text
            node_msg_id = int(chat.get("data-node-msg"))
            user_msg_id = int(chat.get("data-user-msg"))
            by_bot = False
            by_vertex = False
            if last_msg_text.startswith(self.account.bot_character):
                last_msg_text = last_msg_text[1:]
                by_bot = True
            elif last_msg_text.startswith(self.account.old_bot_character):
                last_msg_text = last_msg_text[1:]
                by_vertex = True
            last_msg_text = strip_invisible_suffix(last_msg_text)
            prev_node_msg_id, prev_user_msg_id, prev_text = (
                self.runner_last_messages.get(chat_id) or [-1, -1, None]
            )
            last_msg_text_or_none = (
                None
                if last_msg_text in ("Изображение", "Зображення", "Image")
                else last_msg_text
            )
            if node_msg_id <= prev_node_msg_id:
                continue
            elif (
                not prev_node_msg_id
                and (not prev_user_msg_id)
                and (prev_text == last_msg_text_or_none)
            ):
                self.runner_last_messages[chat_id] = [
                    node_msg_id,
                    user_msg_id,
                    last_msg_text_or_none,
                ]
                continue
            unread = True if "unread" in chat.get("class") else False
            chat_with = chat.find("div", {"class": "media-user-name"}).text
            chat_obj = types.ChatShortcut(
                chat_id,
                chat_with,
                last_msg_text,
                node_msg_id,
                user_msg_id,
                unread,
                str(chat),
            )
            if last_msg_text_or_none is not None:
                chat_obj.last_by_bot = by_bot
                chat_obj.last_by_vertex = by_vertex
            self.account.add_chats([chat_obj])
            self.runner_last_messages[chat_id] = [
                node_msg_id,
                user_msg_id,
                last_msg_text_or_none,
            ]
            if self._Runner__first_request:
                events.append(
                    InitialChatEvent(self._Runner__last_msg_event_tag, chat_obj)
                )
                if self.make_msg_requests:
                    self.last_messages_ids[chat_id] = node_msg_id
                continue
            else:
                lcmc_events.append(
                    LastChatMessageChangedEvent(
                        self._Runner__last_msg_event_tag, chat_obj
                    )
                )
        if lcmc_events:
            events.append(ChatsListChangedEvent(self._Runner__last_msg_event_tag))
        if not self.make_msg_requests:
            events.extend(lcmc_events)
            self._Runner__chat_nodes = {}
            return events
        lcmc_events_without_new_mess = []
        lcmc_events_with_new_mess = []
        lcmc_events_with_chat_node = []
        for lcmc_event in lcmc_events:
            if lcmc_event.chat.node_msg_id <= self.last_messages_ids.get(
                lcmc_event.chat.id, -1
            ):
                lcmc_events_without_new_mess.append(lcmc_event)
            elif (
                lcmc_event.chat.node_msg_id
                <= self._Runner__chat_nodes.get(lcmc_event.chat.id, ({}, -1))[-1]
            ):
                lcmc_events_with_chat_node.append(lcmc_event)
            else:
                lcmc_events_with_new_mess.append(lcmc_event)
        events.extend(lcmc_events_without_new_mess)
        chats_data = {i.chat.id: i.chat.name for i in lcmc_events_with_chat_node}
        chats = [
            self._Runner__chat_nodes.pop(i.chat.id, ({}, -1))[0]
            for i in lcmc_events_with_chat_node
        ]
        new_msg_events = self.generate_new_message_events(
            chats_data=chats_data,
            chats=self.account.parse_chats_histories(chats_data, chats),
        )
        for event in lcmc_events_with_chat_node:
            events.append(event)
            if new_msg_events.get(event.chat.id):
                events.extend(new_msg_events[event.chat.id])
        while lcmc_events_with_new_mess:
            chats_pack = lcmc_events_with_new_mess[: self.runner_len]
            del lcmc_events_with_new_mess[: self.runner_len]
            chats_data = {i.chat.id: i.chat.name for i in chats_pack}
            new_msg_events = self.generate_new_message_events(chats_data)
            for i in chats_pack:
                events.append(i)
                if new_msg_events.get(i.chat.id):
                    events.extend(new_msg_events[i.chat.id])
        return events

    def generate_new_message_events(
        self,
        chats_data: dict[int, str],
        chats: dict[int | str, list[types.Message]] | None = None,
    ) -> dict[int, list[NewMessageEvent]]:
        if chats is None:
            attempts = 3
            while attempts:
                attempts -= 1
                try:
                    chats = self.account.get_chats_histories(
                        chats_data, include_runner_context=True
                    )
                    break
                except exceptions.RequestFailedError as e:
                    _module_state.logger.error(e)
                except:
                    _module_state.logger.error(
                        f"Не удалось получить истории чатов {list(chats_data.keys())}."
                    )
                    _module_state.logger.debug("TRACEBACK", exc_info=True)
                time.sleep(1)
            else:
                _module_state.logger.error(
                    f"Не удалось получить истории чатов {list(chats_data.keys())}: превышено кол-во попыток."
                )
                return {}
        result = {}
        for cid in chats:
            messages = chats[cid]
            result[cid] = []
            self.by_bot_ids[cid] = self.by_bot_ids.get(cid) or []
            if self.last_messages_ids.get(cid):
                messages = [i for i in messages if i.id > self.last_messages_ids[cid]]
            if not messages:
                continue
            if self.by_bot_ids.get(cid):
                for i in messages:
                    if not i.by_bot and i.id in self.by_bot_ids[cid]:
                        i.by_bot = True
            stack = MessageEventsStack()
            if not self.last_messages_ids.get(cid):
                messages = [
                    m
                    for m in messages
                    if m.id > min(self.last_messages_ids.values(), default=10**20)
                ] or messages[-1:]
            self.last_messages_ids[cid] = messages[-1].id
            self.chat_node_tags[cid] = messages[-1].tag
            self.users_ids[cid] = messages[-1].interlocutor_id
            self.by_bot_ids[cid] = [
                i for i in self.by_bot_ids[cid] if i > self.last_messages_ids[cid]
            ]
            for msg in messages:
                event = NewMessageEvent(self._Runner__last_msg_event_tag, msg, stack)
                stack.add_events([event])
                result[cid].append(event)
        return result

    def parse_order_updates(
        self, obj
    ) -> list[
        InitialOrderEvent
        | OrdersListChangedEvent
        | NewOrderEvent
        | OrderStatusChangedEvent
    ]:
        events = []
        self._Runner__last_order_event_tag = obj.get("tag")
        if not self._Runner__first_request:
            events.append(
                OrdersListChangedEvent(
                    self._Runner__last_order_event_tag,
                    obj["data"]["buyer"],
                    obj["data"]["seller"],
                )
            )
        if not self.make_order_requests:
            return events
        attempts = 3
        while attempts:
            attempts -= 1
            try:
                orders_list = self.account.get_sales()[1]
                break
            except exceptions.RequestFailedError as e:
                _module_state.logger.error(e)
            except:
                _module_state.logger.error("Не удалось обновить список заказов.")
                _module_state.logger.debug("TRACEBACK", exc_info=True)
            time.sleep(1)
        else:
            _module_state.logger.error(
                "Не удалось обновить список продаж: превышено кол-во попыток."
            )
            return events
        if (
            self.saved_orders is not None
            and len(self.saved_orders) > len(orders_list)
            or len(orders_list) > 100
        ):
            _module_state.logger.error(
                f"Что-то пошло не так при получении списка заказов."
            )
            _module_state.logger.debug(
                f"SAVED: {(list(self.saved_orders.keys()) if self.saved_orders else self.saved_orders)}"
            )
            _module_state.logger.debug(
                f"ORDERS_LIST ({len(orders_list)}): {[i.id for i in orders_list]}"
            )
            return events
        now_orders = {}
        for order in orders_list:
            now_orders[order.id] = order
            if self.saved_orders is None:
                events.append(
                    InitialOrderEvent(self._Runner__last_order_event_tag, order)
                )
            elif order.id not in self.saved_orders:
                events.append(NewOrderEvent(self._Runner__last_order_event_tag, order))
                if order.status == types.OrderStatuses.CLOSED:
                    events.append(
                        OrderStatusChangedEvent(
                            self._Runner__last_order_event_tag, order
                        )
                    )
            elif order.status != self.saved_orders[order.id].status:
                events.append(
                    OrderStatusChangedEvent(self._Runner__last_order_event_tag, order)
                )
        self.saved_orders = now_orders
        return events

    def update_last_message(
        self, chat_id: int, message_id: int, message_text: str | None
    ):
        self.runner_last_messages[chat_id] = [message_id, message_id, message_text]
