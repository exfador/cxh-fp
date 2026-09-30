from __future__ import annotations
import random
import time
import uuid
from typing import TYPE_CHECKING
import requests

if TYPE_CHECKING:
    pass
from FunPayAPI.updater.events import *
import FunPayAPI.updater.runner as _module_state


class RequestProcessing:
    def _Runner__add_payload(self, payload: dict):
        id_ = str(uuid.uuid4())
        self.payload_queue[id_] = payload
        return id_

    def get_result(self, payload: dict) -> requests.Response:
        id_ = self._Runner__add_payload(payload)
        while id_ in self.payload_queue:
            time.sleep(0.1)
        for i in range(300):
            if id_ in self.runner_results:
                break
            time.sleep(0.1)
        result = self.runner_results.pop(
            id_, Exception("Что-то пошло не так во время получения результата")
        )
        if isinstance(result, Exception):
            raise result
        return result

    def _Runner__detect_chats_with_activity(self, amount: int) -> list[int]:
        if not self._Runner__chat_bookmarks or len(self._Runner__chat_bookmarks) < 2:
            return []
        new_list = self._Runner__chat_bookmarks[-1]["data"]["order"]
        old_list = random.choice(self._Runner__chat_bookmarks[:-1])["data"]["order"]
        old_positions = {chat_id: i for i, chat_id in enumerate(old_list)}
        last = float("inf")
        split_index = len(new_list)
        for i in range(len(new_list) - 1, -1, -1):
            idx = old_positions.get(new_list[i])
            if idx is None or i < idx or last < idx:
                split_index = i
                break
            else:
                last = idx
        result = new_list[: split_index + 1]
        if len(result) >= amount:
            return random.sample(result, amount)
        i = 0
        result = set(result)
        while len(result) < amount and i < len(new_list):
            result.add(new_list[i])
            i += 1
        return list(result)

    def _Runner__fill_request_data(self, request_data: dict) -> dict:
        if not self._Runner__first_request:
            if (
                len(request_data["objects"]) < self.runner_len
                and (not self._Runner__orders_counters)
                and (
                    "orders_counters"
                    not in [i["type"] for i in request_data["objects"]]
                )
            ):
                request_data["objects"].extend(
                    self.account.get_payload_data(
                        last_order_event_tag=self._Runner__last_order_event_tag
                    )["objects"]
                )
            if (
                len(request_data["objects"]) < self.runner_len
                and time.time() - self._Runner__chat_bookmarks_time
                > 1.5 ** len(self._Runner__chat_bookmarks) - 1
                and (
                    "chat_bookmarks" not in [i["type"] for i in request_data["objects"]]
                )
            ):
                request_data["objects"].extend(
                    self.account.get_payload_data(
                        last_msg_event_tag=self._Runner__last_msg_event_tag
                    )["objects"]
                )
                self._Runner__chat_bookmarks_time = time.time()
        try:
            if (
                self.make_msg_requests
                and (remaining := (self.runner_len - len(request_data["objects"]))) > 0
            ):
                payload_data = self.account.get_payload_data(
                    chats_data=self._Runner__detect_chats_with_activity(remaining),
                    include_runner_context=True,
                )
                request_data["objects"].extend(payload_data["objects"])
        except:
            _module_state.logger.warning(
                "Что-то пошло не так во время подкидывания чатов."
            )
            _module_state.logger.debug("TRACEBACK", exc_info=True)
        return request_data

    def loop(self):
        if self._Runner__is_running:
            return
        self._Runner__is_running = True
        while True:
            try:
                request_data = {"objects": [], "request": False}
                ids = set()
                for id_ in list(self.payload_queue.keys()):
                    payload = self.payload_queue.get(id_)
                    if payload is None:
                        continue
                    if (
                        not request_data["objects"]
                        and (not request_data["request"])
                        or (
                            len(request_data["objects"]) + len(payload["objects"])
                            <= self.runner_len
                            and int(bool(request_data["request"]))
                            + int(bool(payload["request"]))
                            <= 1
                        )
                    ):
                        request_data["objects"].extend(payload["objects"])
                        request_data["request"] = (
                            request_data["request"] or payload["request"]
                        )
                        ids.add(id_)
                        self.payload_queue.pop(id_, None)
                    else:
                        break
                if not request_data["objects"] and (not request_data["request"]):
                    time.sleep(0.1)
                    continue
                types_ = [i["type"] for i in request_data["objects"]]
                if "orders_counters" in types_ and "chat_bookmarks" in types_:
                    is_listener_request = True
                else:
                    is_listener_request = False
                request_data = self._Runner__fill_request_data(request_data)
                try:
                    result = self.account.runner_request(request_data)
                except Exception as e:
                    result = e
                for id_ in ids:
                    self.runner_results[id_] = result
                if isinstance(result, Exception):
                    time.sleep(5)
                    continue
                try:
                    result = result.json()
                    for obj in result["objects"]:
                        if not is_listener_request and obj["type"] == "orders_counters":
                            self._Runner__orders_counters = obj
                        elif (
                            obj["type"] == "chat_bookmarks"
                            and (data := obj.get("data"))
                            and data.get("order")
                        ):
                            if not is_listener_request:
                                self._Runner__chat_bookmarks.append(obj)
                        elif self.make_msg_requests and (
                            obj["type"] == "chat_node"
                            and (data := obj.get("data"))
                            and (node := data.get("node"))
                            and (node_id := node.get("id"))
                            and (messages := data.get("messages"))
                        ):
                            last_msg_id = messages[-1]["id"]
                            if last_msg_id > self.last_messages_ids.get(
                                node_id, 0
                            ) and (
                                node_id not in self._Runner__chat_nodes
                                or last_msg_id > self._Runner__chat_nodes[node_id][-1]
                            ):
                                self._Runner__chat_nodes[node_id] = (obj, last_msg_id)
                except:
                    _module_state.logger.warning(
                        "Что-то пошло не так во время разбора ответа Runner"
                    )
                    _module_state.logger.debug("TRACEBACK", exc_info=True)
            except:
                _module_state.logger.error("Бабах")
                _module_state.logger.debug("TRACEBACK", exc_info=True)

    def get_updates(self) -> dict:
        response = self.account.abuse_runner(
            last_msg_event_tag=self._Runner__last_msg_event_tag,
            last_order_event_tag=self._Runner__last_order_event_tag,
        )
        json_response = response.json()
        return json_response

    def parse_updates(
        self, updates_objects: list[dict]
    ) -> list[
        InitialChatEvent
        | ChatsListChangedEvent
        | LastChatMessageChangedEvent
        | NewMessageEvent
        | InitialOrderEvent
        | OrdersListChangedEvent
        | NewOrderEvent
        | OrderStatusChangedEvent
    ]:
        events = []
        for obj in sorted(
            updates_objects,
            key=lambda x: x.get("type") == "orders_counters",
            reverse=True,
        ):
            if obj.get("type") == "chat_bookmarks":
                events.extend(self.parse_chat_updates(obj))
            elif obj.get("type") == "orders_counters":
                events.extend(self.parse_order_updates(obj))
        if self._Runner__first_request:
            self._Runner__first_request = False
        return events
