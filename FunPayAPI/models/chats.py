from __future__ import annotations
from typing import Optional
from FunPayAPI.common.utils import RegularExpressions
from FunPayAPI.common.enums import (
    MessageTypes,
    OrderStatuses,
    SubCategoryTypes,
    Currency,
)
import datetime
import FunPayAPI.types as _module_state


class BaseOrderInfo:
    def __init__(self):
        self._order: _module_state.Order | None = None
        self._order_attempt_made: bool = False
        self._order_attempt_error: bool = False


class ChatShortcut(BaseOrderInfo):
    def __init__(
        self,
        id_: int,
        name: str,
        last_message_text: str,
        node_msg_id: int,
        user_msg_id: int,
        unread: bool,
        html: str,
        determine_msg_type: bool = True,
    ):
        self.id: int = id_
        self.name: str | None = name if name else None
        self.last_message_text: str = last_message_text
        self.last_by_bot: bool | None = None
        self.last_by_vertex: bool | None = None
        self.unread: bool = unread
        self.node_msg_id: int = node_msg_id
        self.user_msg_id: int = user_msg_id
        self.last_message_type: MessageTypes | None = (
            None if not determine_msg_type else self.get_last_message_type()
        )
        self.html: str = html
        _module_state.BaseOrderInfo.__init__(self)

    def get_last_message_type(self) -> MessageTypes:
        res = RegularExpressions()
        if res.DISCORD.search(self.last_message_text):
            return MessageTypes.DISCORD
        if res.DEAR_VENDORS.search(self.last_message_text):
            return MessageTypes.DEAR_VENDORS
        if res.ORDER_PURCHASED.findall(
            self.last_message_text
        ) and res.ORDER_PURCHASED2.findall(self.last_message_text):
            return MessageTypes.ORDER_PURCHASED
        if res.ORDER_ID.search(self.last_message_text) is None:
            return MessageTypes.NON_SYSTEM
        sys_msg_types = {
            MessageTypes.ORDER_CONFIRMED: res.ORDER_CONFIRMED,
            MessageTypes.NEW_FEEDBACK: res.NEW_FEEDBACK,
            MessageTypes.NEW_FEEDBACK_ANSWER: res.NEW_FEEDBACK_ANSWER,
            MessageTypes.FEEDBACK_CHANGED: res.FEEDBACK_CHANGED,
            MessageTypes.FEEDBACK_DELETED: res.FEEDBACK_DELETED,
            MessageTypes.REFUND: res.REFUND,
            MessageTypes.FEEDBACK_ANSWER_CHANGED: res.FEEDBACK_ANSWER_CHANGED,
            MessageTypes.FEEDBACK_ANSWER_DELETED: res.FEEDBACK_ANSWER_DELETED,
            MessageTypes.ORDER_CONFIRMED_BY_ADMIN: res.ORDER_CONFIRMED_BY_ADMIN,
            MessageTypes.PARTIAL_REFUND: res.PARTIAL_REFUND,
            MessageTypes.ORDER_REOPENED: res.ORDER_REOPENED,
            MessageTypes.REFUND_BY_ADMIN: res.REFUND_BY_ADMIN,
        }
        for i in sys_msg_types:
            if sys_msg_types[i].search(self.last_message_text):
                return i
        else:
            return MessageTypes.NON_SYSTEM

    def __str__(self):
        return self.last_message_text


class BuyerViewing:
    def __init__(
        self,
        buyer_id: int,
        link: str | None,
        text: str | None,
        tag: str | None,
        html: str | None = None,
    ):
        self.buyer_id: int = buyer_id
        self.link: str | None = link
        self.text: str | None = text
        self.tag: str | None = tag
        self.html: str | None = html
        self.is_viewing_lot: bool = bool(self.link)

    @property
    def lot_id(self) -> str | int | None:
        if self.is_viewing_lot:
            id_ = self.link.split("=")[-1]
            return int(id_) if id_.isdigit() else id_
        else:
            return None

    @property
    def subcategory_type(self) -> SubCategoryTypes | None:
        if self.is_viewing_lot:
            return (
                SubCategoryTypes.COMMON
                if "/lots/" in self.link
                else SubCategoryTypes.CURRENCY
            )
        else:
            return None


class Chat:
    def __init__(
        self,
        id_: int,
        name: str,
        looking_link: str | None,
        looking_text: str | None,
        html: str,
        messages: Optional[list[Message]] = None,
    ):
        self.id: int = id_
        self.name: str = name
        self.looking_link: str | None = looking_link
        self.looking_text: str | None = looking_text
        self.html: str = html
        self.messages: list[_module_state.Message] = messages or []


class Message(BaseOrderInfo):
    def __init__(
        self,
        id_: int,
        text: str | None,
        chat_id: int | str,
        chat_name: str | None,
        interlocutor_id: int | None,
        author: str | None,
        author_id: int,
        html: str,
        image_link: str | None = None,
        image_name: str | None = None,
        determine_msg_type: bool = True,
        badge_text: Optional[str] = None,
        tag: Optional[str] = None,
    ):
        self.id: int = id_
        self.text: str | None = text
        self.chat_id: int | str = chat_id
        self.chat_name: str | None = chat_name
        self.interlocutor_id: int | None = interlocutor_id
        self.buyer_viewing: _module_state.BuyerViewing | None = None
        self.type: MessageTypes | None = (
            None if not determine_msg_type else self.get_message_type()
        )
        self.author: str | None = author
        self.author_id: int = author_id
        self.html: str = html
        self.image_link: str | None = image_link
        self.image_name: str | None = image_name
        self.by_bot: bool = False
        self.by_vertex: bool = False
        self.badge: str | None = badge_text
        self.is_employee: bool = False
        self.is_support: bool = False
        self.is_moderation: bool = False
        self.is_arbitration: bool = False
        self.is_autoreply: bool = False
        self.initiator_username: str | None = None
        self.initiator_id: int | None = None
        self.i_am_seller: bool | None = None
        self.i_am_buyer: bool | None = None
        self.tag: str | None = tag
        _module_state.BaseOrderInfo.__init__(self)

    def get_message_type(self) -> MessageTypes:
        if not self.text:
            return MessageTypes.NON_SYSTEM
        res = RegularExpressions()
        if res.DISCORD.search(self.text):
            return MessageTypes.DISCORD
        if res.DEAR_VENDORS.search(self.text):
            return MessageTypes.DEAR_VENDORS
        if res.ORDER_PURCHASED.findall(self.text) and res.ORDER_PURCHASED2.findall(
            self.text
        ):
            return MessageTypes.ORDER_PURCHASED
        if res.ORDER_ID.search(self.text) is None:
            return MessageTypes.NON_SYSTEM
        sys_msg_types = {
            MessageTypes.ORDER_CONFIRMED: res.ORDER_CONFIRMED,
            MessageTypes.NEW_FEEDBACK: res.NEW_FEEDBACK,
            MessageTypes.NEW_FEEDBACK_ANSWER: res.NEW_FEEDBACK_ANSWER,
            MessageTypes.FEEDBACK_CHANGED: res.FEEDBACK_CHANGED,
            MessageTypes.FEEDBACK_DELETED: res.FEEDBACK_DELETED,
            MessageTypes.REFUND: res.REFUND,
            MessageTypes.FEEDBACK_ANSWER_CHANGED: res.FEEDBACK_ANSWER_CHANGED,
            MessageTypes.FEEDBACK_ANSWER_DELETED: res.FEEDBACK_ANSWER_DELETED,
            MessageTypes.ORDER_CONFIRMED_BY_ADMIN: res.ORDER_CONFIRMED_BY_ADMIN,
            MessageTypes.PARTIAL_REFUND: res.PARTIAL_REFUND,
            MessageTypes.ORDER_REOPENED: res.ORDER_REOPENED,
            MessageTypes.REFUND_BY_ADMIN: res.REFUND_BY_ADMIN,
        }
        for i in sys_msg_types:
            if sys_msg_types[i].search(self.text):
                return i
        else:
            return MessageTypes.NON_SYSTEM

    def __str__(self):
        return (
            self.text
            if self.text is not None
            else self.image_link
            if self.image_link is not None
            else ""
        )


class OrderShortcut(BaseOrderInfo):
    def __init__(
        self,
        id_: str,
        description: str,
        price: float,
        currency: Currency,
        buyer_username: str,
        buyer_id: int,
        chat_id: int | str,
        status: OrderStatuses,
        date: datetime.datetime,
        subcategory_name: str,
        subcategory: _module_state.SubCategory | None,
        html: str,
        dont_search_amount: bool = False,
    ):
        self.id: str = id_ if not id_.startswith("#") else id_[1:]
        self.description: str = description
        self.price: float = price
        self.currency: Currency = currency
        self.amount: int | None = (
            self.parse_amount() if not dont_search_amount else None
        )
        self.buyer_username: str = buyer_username
        self.buyer_id: int = buyer_id
        self.chat_id: int | str = chat_id
        self.status: OrderStatuses = status
        self.date: datetime.datetime = date
        self.subcategory_name: str = subcategory_name
        self.subcategory: _module_state.SubCategory | None = subcategory
        self.html: str = html
        _module_state.BaseOrderInfo.__init__(self)

    def parse_amount(self) -> int:
        res = RegularExpressions()
        result = res.PRODUCTS_AMOUNT.findall(self.description)
        if result:
            return int(result[0][0].replace(" ", ""))
        return 1

    def __str__(self):
        return self.description


class Server:
    def __init__(self, id_: int, name: str | None = None):
        self.id: int = id_
        self.name = name
