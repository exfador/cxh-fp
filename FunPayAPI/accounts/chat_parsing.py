from __future__ import annotations
from FunPayAPI.common.constants import CHAT_IMAGE_MARKER
from typing import TYPE_CHECKING, Optional
from FunPayAPI.common.utils import strip_invisible_suffix

if TYPE_CHECKING:
    pass
from bs4 import BeautifulSoup
import json
from FunPayAPI import types
import FunPayAPI.account as _module_state


class ChatParser:
    def _Account__parse_messages(
        self,
        json_messages: dict,
        chat_id: int | str,
        interlocutor_id: Optional[int] = None,
        interlocutor_username: Optional[str] = None,
        from_id: int = 0,
        is_private: bool | None = None,
        tag: str | None = None,
    ) -> list[types.Message]:
        messages = []
        ids = {self.id: self.username, 0: "FunPay"}
        badges = {}
        mb_chat_is_private = (
            is_private
            or interlocutor_id
            or interlocutor_username
            or (is_private is None and self.chat_id_private(chat_id))
        )
        if None not in (interlocutor_id, interlocutor_username):
            ids[interlocutor_id] = interlocutor_username
        for i in json_messages:
            if i["id"] < from_id:
                continue
            author_id = i["author"]
            parser = BeautifulSoup(i["html"].replace("<br>", "\n"), "lxml")
            if None in [ids.get(author_id), badges.get(author_id)] and (
                author_div := parser.find("div", {"class": "media-user-name"})
            ):
                if badges.get(author_id) is None:
                    badge = author_div.find(
                        "span", {"class": "chat-msg-author-label label label-success"}
                    )
                    badges[author_id] = badge.text if badge else 0
                if ids.get(author_id) is None:
                    author = author_div.find("a").text.strip()
                    ids[author_id] = author
                    if mb_chat_is_private:
                        if author_id == interlocutor_id and (not interlocutor_username):
                            interlocutor_username = author
                        elif interlocutor_username == author and (not interlocutor_id):
                            interlocutor_id = author_id
            by_bot = False
            by_vertex = False
            image_name = None
            if mb_chat_is_private and (
                image_tag := parser.find("a", {"class": "chat-img-link"})
            ):
                image_name = image_tag.find("img")
                image_name = image_name.get("alt") if image_name else None
                image_link = image_tag.get("href")
                message_text = None
                if (
                    isinstance(image_name, str)
                    and CHAT_IMAGE_MARKER in image_name.lower()
                ):
                    by_bot = True
                elif image_name == "funpay_vertex_image.png":
                    by_vertex = True
            else:
                image_link = None
                if author_id == 0:
                    message_text = parser.find("div", role="alert").text.strip()
                else:
                    message_text = parser.find("div", {"class": "chat-msg-text"}).text
                message_text = strip_invisible_suffix(message_text)
                if message_text.startswith(self._Account__bot_character) or (
                    message_text.startswith(self._Account__old_bot_character)
                    and author_id == self.id
                ):
                    message_text = message_text[1:]
                    by_bot = True
            message_obj = types.Message(
                i["id"],
                message_text,
                chat_id,
                interlocutor_username,
                interlocutor_id,
                None,
                author_id,
                i["html"],
                image_link,
                image_name,
                determine_msg_type=False,
                tag=tag,
            )
            message_obj.by_bot = by_bot
            message_obj.by_vertex = by_vertex
            message_obj.type = (
                types.MessageTypes.NON_SYSTEM
                if author_id != 0
                else message_obj.get_message_type()
            )
            messages.append(message_obj)
        for i in messages:
            i.author = ids.get(i.author_id)
            i.chat_name = interlocutor_username
            i.interlocutor_id = interlocutor_id
            i.badge = badges.get(i.author_id) if badges.get(i.author_id) != 0 else None
            parser = BeautifulSoup(i.html, "lxml")
            if i.badge:
                i.is_employee = True
                if i.badge in ("поддержка", "підтримка", "support"):
                    i.is_support = True
                elif i.badge in ("модерация", "модерація", "moderation"):
                    i.is_moderation = True
                elif i.badge in ("арбитраж", "арбітраж", "arbitration"):
                    i.is_arbitration = True
            default_label = parser.find("div", {"class": "media-user-name"})
            default_label = (
                default_label.find(
                    "span", {"class": "chat-msg-author-label label label-default"}
                )
                if default_label
                else None
            )
            if default_label:
                if default_label.text in ("автовідповідь", "автоответ", "auto-reply"):
                    i.is_autoreply = True
            i.badge = (
                default_label.text
                if i.badge is None and default_label is not None
                else i.badge
            )
            if i.type != types.MessageTypes.NON_SYSTEM:
                users = parser.find_all(
                    "a", href=lambda href: href and "/users/" in href
                )
                if users:
                    i.initiator_username = users[0].text
                    i.initiator_id = int(users[0]["href"].split("/")[-2])
                    if i.type in (
                        types.MessageTypes.ORDER_PURCHASED,
                        types.MessageTypes.ORDER_CONFIRMED,
                        types.MessageTypes.NEW_FEEDBACK,
                        types.MessageTypes.FEEDBACK_CHANGED,
                        types.MessageTypes.FEEDBACK_DELETED,
                    ):
                        if i.initiator_id == self.id:
                            i.i_am_seller = False
                            i.i_am_buyer = True
                        else:
                            i.i_am_seller = True
                            i.i_am_buyer = False
                    elif i.type in (
                        types.MessageTypes.NEW_FEEDBACK_ANSWER,
                        types.MessageTypes.FEEDBACK_ANSWER_CHANGED,
                        types.MessageTypes.FEEDBACK_ANSWER_DELETED,
                        types.MessageTypes.REFUND,
                    ):
                        if i.initiator_id == self.id:
                            i.i_am_seller = True
                            i.i_am_buyer = False
                        else:
                            i.i_am_seller = False
                            i.i_am_buyer = True
                    elif len(users) > 1:
                        last_user_id = int(users[-1]["href"].split("/")[-2])
                        if i.type == types.MessageTypes.ORDER_CONFIRMED_BY_ADMIN:
                            if last_user_id == self.id:
                                i.i_am_seller = True
                                i.i_am_buyer = False
                            else:
                                i.i_am_seller = False
                                i.i_am_buyer = True
                        elif i.type == types.MessageTypes.REFUND_BY_ADMIN:
                            if last_user_id == self.id:
                                i.i_am_seller = False
                                i.i_am_buyer = True
                            else:
                                i.i_am_seller = True
                                i.i_am_buyer = False
        return messages

    def _Account__update_csrf_token(self, parser: BeautifulSoup):
        try:
            app_data = json.loads(parser.find("body").get("data-app-data"))
            self.csrf_token = app_data.get("csrf-token") or self.csrf_token
        except:
            _module_state.logger.warning("Произошла ошибка при обновлении csrf.")
            _module_state.logger.debug("TRACEBACK", exc_info=True)

    @staticmethod
    def _Account__parse_buyer_viewing(json_buyer_viewing: dict) -> types.BuyerViewing:
        buyer_id = json_buyer_viewing.get("id")
        if not json_buyer_viewing["data"]:
            return types.BuyerViewing(buyer_id, None, None, None, None)
        tag = json_buyer_viewing["tag"]
        html = json_buyer_viewing["data"]["html"]
        if html:
            html = html["desktop"]
            element = BeautifulSoup(html, "lxml").find("a")
            link, text = (element.get("href"), element.text)
        else:
            html, link, text = (None, None, None)
        return types.BuyerViewing(buyer_id, link, text, tag, html)
