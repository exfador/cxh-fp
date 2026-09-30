from __future__ import annotations
from FunPayAPI.common.constants import CHAT_IMAGE_NAME
from typing import TYPE_CHECKING, Literal, Optional, IO

if TYPE_CHECKING:
    pass
from requests_toolbelt import MultipartEncoder
from bs4 import BeautifulSoup
import requests
from html import escape
from FunPayAPI.accounts.constants import MESSAGE_PARSE_FAILURE, CHAT_HISTORY_PATH
from FunPayAPI.accounts.chat_context import parse_history_response, parse_histories
from FunPayAPI.security.urls import build_api_query
import random
import string
import time
from FunPayAPI import types
from FunPayAPI.common import exceptions
import FunPayAPI.account as _module_state


class ChatOperations:
    def get_balance(self, lot_id: int) -> types.Balance:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        response = self.method(
            "get", f"lots/offer?id={lot_id}", {"accept": "*/*"}, {}, raise_not_200=True
        )
        html_response = response.content.decode()
        parser = BeautifulSoup(html_response, "lxml")
        username = parser.find("div", {"class": "user-link-name"})
        if not username:
            raise exceptions.UnauthorizedError(response)
        self._Account__update_csrf_token(parser)
        balances = parser.find("select", {"name": "method"})
        balance = types.Balance(
            float(balances["data-balance-total-rub"]),
            float(balances["data-balance-rub"]),
            float(balances["data-balance-total-usd"]),
            float(balances["data-balance-usd"]),
            float(balances["data-balance-total-eur"]),
            float(balances["data-balance-eur"]),
        )
        return balance

    def get_chat_history(
        self,
        chat_id: int | str,
        last_message_id: int | None = None,
        interlocutor_username: Optional[str] = None,
        from_id: int = 0,
    ) -> list[types.Message]:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if last_message_id is None:
            return self.get_chats_histories({chat_id: interlocutor_username}).get(
                chat_id, []
            )
        query = build_api_query(
            CHAT_HISTORY_PATH, {"node": chat_id, "last_message": last_message_id}
        )
        response = self.method(
            "get",
            query,
            {"accept": "*/*", "x-requested-with": "XMLHttpRequest"},
            {},
            raise_not_200=True,
        )
        return parse_history_response(
            self, response.json(), interlocutor_username, from_id
        )

    def parse_chats_histories(
        self,
        chats_data: dict[int | str, str | None] | list[int | str],
        objects: list[dict],
    ) -> dict[int | str, list[types.Message]]:
        return parse_histories(self, chats_data, objects)

    def get_chats_histories(
        self,
        chats_data: dict[int | str, str | None],
        include_runner_context: bool = False,
    ) -> dict[int | str, list[types.Message]]:
        response = self.abuse_runner(
            chats_data=chats_data, include_runner_context=include_runner_context
        )
        objects = response.json()["objects"]
        return self.parse_chats_histories(chats_data, objects)

    def upload_image(
        self, image: str | IO[bytes], type_: Literal["chat", "offer"] = "chat"
    ) -> int:
        assert type_ in ("chat", "offer")
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if isinstance(image, str):
            with open(image, "rb") as f:
                img = f.read()
        else:
            img = image
        fields = {"file": (CHAT_IMAGE_NAME, img, "image/png"), "file_id": "0"}
        boundary = "----WebKitFormBoundary" + "".join(
            random.sample(string.ascii_letters + string.digits, 16)
        )
        m = MultipartEncoder(fields=fields, boundary=boundary)
        headers = {
            "accept": "*/*",
            "x-requested-with": "XMLHttpRequest",
            "content-type": m.content_type,
        }
        response = self.method("post", f"file/add{type_.title()}Image", headers, m)
        if response.status_code == 400:
            try:
                json_response = response.json()
                message = json_response.get("msg")
                raise exceptions.ImageUploadError(response, message)
            except requests.exceptions.JSONDecodeError:
                raise exceptions.ImageUploadError(response, None)
        elif response.status_code != 200:
            raise exceptions.RequestFailedError(response)
        if not (document_id := response.json().get("fileId")):
            raise exceptions.ImageUploadError(response, None)
        return int(document_id)

    def send_message(
        self,
        chat_id: int | str,
        text: Optional[str] = None,
        chat_name: Optional[str] = None,
        interlocutor_id: Optional[int] = None,
        image_id: Optional[int] = None,
        add_to_ignore_list: bool = True,
        update_last_saved_message: bool = False,
        leave_as_unread: bool = False,
    ) -> types.Message:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        request = {
            "action": "chat_message",
            "data": {"node": chat_id, "last_message": -1, "content": text},
        }
        if image_id is not None:
            request["data"]["image_id"] = image_id
            request["data"]["content"] = ""
        else:
            request["data"]["content"] = (
                f"{self._Account__bot_character}{text}" if text else ""
            )
        chats_data = None if leave_as_unread else {chat_id: chat_name}
        response = self.abuse_runner(chats_data=chats_data, request=request)
        json_response = response.json()
        if not (resp := json_response.get("response")):
            raise exceptions.MessageNotDeliveredError(response, None, chat_id)
        if (error_text := resp.get("error")) is not None:
            if error_text in (
                "Нельзя отправлять сообщения слишком часто.",
                "You cannot send messages too frequently.",
                "Не можна надсилати повідомлення занадто часто.",
            ):
                self.last_flood_err_time = time.time()
            elif error_text in (
                "Нельзя слишком часто отправлять сообщения разным пользователям.",
                "Не можна надто часто надсилати повідомлення різним користувачам.",
                "You cannot message multiple users too frequently.",
            ):
                self.last_multiuser_flood_err_time = time.time()
            raise exceptions.MessageNotDeliveredError(response, error_text, chat_id)
        obj = next(
            iter(
                [
                    i
                    for i in json_response["objects"]
                    if i["type"] == "chat_node"
                    and chat_id
                    in (
                        i["data"]["node"]["id"],
                        str(i["data"]["node"]["id"]),
                        i["data"]["node"]["name"],
                    )
                ]
            ),
            None,
        )
        is_private_chat = True
        if obj is None:
            message_text = text
            safe_text = escape(message_text or "", quote=False)
            fake_html = f'\n            <div class="chat-msg-item" id="message-0000000000">\n                <div class="chat-message">\n                    <div class="chat-msg-body">\n                        <div class="chat-msg-text">{safe_text}</div>\n                    </div>\n                </div>\n            </div>\n            '
            message_obj = types.Message(
                0,
                message_text,
                chat_id,
                chat_name,
                interlocutor_id,
                self.username,
                self.id,
                fake_html,
                None,
                None,
            )
        else:
            tag = obj["tag"]
            mes = obj["data"]["messages"][-1]
            parser = BeautifulSoup(mes["html"].replace("<br>", "\n"), "lxml")
            image_name = None
            image_link = None
            message_text = None
            chat_id = obj["data"]["node"]["id"]
            is_private_chat = not obj["data"]["node"]["silent"]
            try:
                if image_tag := parser.find("a", {"class": "chat-img-link"}):
                    image_name = image_tag.find("img")
                    image_name = image_name.get("alt") if image_name else None
                    image_link = image_tag.get("href")
                else:
                    message_text = parser.find(
                        "div", {"class": "chat-msg-text"}
                    ).text.replace(self._Account__bot_character, "", 1)
            except (AttributeError, KeyError, TypeError, ValueError):
                _module_state.logger.warning(MESSAGE_PARSE_FAILURE)
                raise
            message_obj = types.Message(
                int(mes["id"]),
                message_text,
                chat_id,
                chat_name,
                interlocutor_id,
                self.username,
                self.id,
                mes["html"],
                image_link,
                image_name,
                tag=tag,
            )
        if self.runner and is_private_chat and isinstance(chat_id, int):
            if add_to_ignore_list and message_obj.id:
                self.runner.mark_as_by_bot(chat_id, message_obj.id)
            if update_last_saved_message:
                self.runner.update_last_message(
                    chat_id, message_obj.id, message_obj.text
                )
        return message_obj

    def send_image(
        self,
        chat_id: int,
        image: int | str | IO[bytes],
        chat_name: Optional[str] = None,
        interlocutor_id: Optional[int] = None,
        add_to_ignore_list: bool = True,
        update_last_saved_message: bool = False,
        leave_as_unread: bool = False,
    ) -> types.Message:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if not isinstance(image, int):
            image = self.upload_image(image, type_="chat")
        result = self.send_message(
            chat_id,
            None,
            chat_name,
            interlocutor_id,
            image,
            add_to_ignore_list,
            update_last_saved_message,
            leave_as_unread,
        )
        return result
