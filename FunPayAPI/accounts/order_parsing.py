from __future__ import annotations
from FunPayAPI.security.urls import normalize_api_url, is_api_method
from typing import TYPE_CHECKING, Literal
from FunPayAPI.common.utils import parse_currency

if TYPE_CHECKING:
    pass
from FunPayAPI import types
from FunPayAPI.common import enums
import FunPayAPI.account as _module_state


class OrderParser:
    def _Account__parse_order(
        self, order_data: dict, locale: Literal["ru", "en", "uk"]
    ) -> types.Order:
        id_ = order_data["order_uid"]
        node_id = order_data["section"]["local_id"]
        subcategory_type = (
            types.SubCategoryTypes.COMMON
            if order_data["section"]["type_id"] == "lot"
            else types.SubCategoryTypes.CURRENCY
        )
        subcategory = self.get_subcategory(subcategory_type, node_id)
        buyer = order_data["buyer"]
        seller = order_data["seller"]
        buyer_id, seller_id = (buyer["user_id"], seller["user_id"])
        buyer_username, seller_username = (buyer.get("name"), seller.get("name"))
        currency = parse_currency(order_data["currency"])
        price = float(order_data["amount"])
        status_str = order_data["status"]
        status = {
            "unpaid": enums.OrderStatuses.UNPAID,
            "paid": enums.OrderStatuses.PAID,
            "closed": enums.OrderStatuses.CLOSED,
            "refunded": enums.OrderStatuses.REFUNDED,
            "partially_refunded": enums.OrderStatuses.PARTIALLY_REFUNDED,
        }[status_str]
        chat_id = order_data["chat"]["node_name"]
        review = order_data.get("review")
        if review:
            text = review["text"]
            rating = review["rating"]
            reply = review["reply"]
            hidden = review["hidden"]
            if text or rating or reply:
                review = types.Review(
                    rating,
                    text,
                    reply,
                    False,
                    "",
                    hidden,
                    id_,
                    buyer_username,
                    buyer_id,
                    bool(text and text.endswith(self.bot_character)),
                    bool(reply and reply.endswith(self.bot_character)),
                )
            else:
                review = None
        type_data = order_data.get("type_data", {})
        amount = type_data.get("amount")
        if amount:
            amount = float(type_data["amount"])
            amount = int(amount) if int(amount) == amount else amount
        player = type_data.get("player") or None
        secrets = [i["value"] for i in type_data.get("secrets", [])]
        server = type_data.get("server")
        if server:
            server = types.Server(server["server_id"], server.get("name"))
        side = type_data.get("side")
        if side:
            side = types.Side(side["side_id"], side.get("name"))
        fields = {
            key: types.LotField(
                key, value["value"], value["name"], value["field_type_id"]
            )
            for key, value in type_data.get("fields", {}).items()
        }
        return types.Order(
            id_,
            status,
            subcategory,
            server,
            side,
            fields,
            amount,
            price,
            currency,
            player,
            buyer_id,
            buyer_username,
            seller_id,
            seller_username,
            chat_id,
            review,
            secrets,
            locale,
        )

    @staticmethod
    def chat_id_private(chat_id: int | str):
        return isinstance(chat_id, int) or _module_state.PRIVATE_CHAT_ID_RE.fullmatch(
            chat_id
        )

    @property
    def bot_character(self) -> str:
        return self._Account__bot_character

    @property
    def old_bot_character(self) -> str:
        return self._Account__old_bot_character

    @property
    def zero_width_suffix(self) -> str:
        return " \u200b\u200d\u200c"

    @property
    def locale(self) -> Literal["ru", "en", "uk"] | None:
        return self._Account__locale

    @locale.setter
    def locale(self, new_locale: Literal["ru", "en", "uk"]):
        if self._Account__locale != new_locale and new_locale in ("ru", "en", "uk"):
            self._Account__set_locale = new_locale

    def normalize_url(
        self, api_method: str, locale: Literal["ru", "en", "uk"] | None = None
    ) -> str:
        return normalize_api_url(api_method, locale or self.locale)

    @staticmethod
    def is_funpay_api_method(api_method: str):
        return is_api_method(api_method)
