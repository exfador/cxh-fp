from __future__ import annotations
from typing import TYPE_CHECKING, Literal
import FunPayAPI.common.enums
from FunPayAPI.common.utils import parse_currency, strip_invisible_suffix
from FunPayAPI.types import PaymentMethod, CalcResult

if TYPE_CHECKING:
    pass
from bs4 import BeautifulSoup
import json
from FunPayAPI import types
from FunPayAPI.accounts.offer_forms import parse_lot_fields, parse_chip_fields
from FunPayAPI.security.urls import build_api_query
from FunPayAPI.common import exceptions, utils, enums


class OfferChatQueries:
    def get_lot_price_quote(self, lot_id: int, price=None) -> types.LotPriceQuote:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        from FunPayAPI.accounts.price_quotes import get_lot_price_quote

        return get_lot_price_quote(self, lot_id, price)

    def request_chats(self) -> list[types.ChatShortcut]:
        response = self.abuse_runner(last_msg_event_tag=utils.random_tag())
        json_response = response.json()
        msgs = ""
        for obj in json_response["objects"]:
            if obj.get("type") != "chat_bookmarks":
                continue
            msgs = obj["data"]["html"]
        if not msgs:
            return []
        parser = BeautifulSoup(msgs, "lxml")
        chats = parser.find_all("a", {"class": "contact-item"})
        chats_objs = []
        for msg in chats:
            chat_id = int(msg["data-id"])
            if not (
                last_msg_text := msg.find("div", {"class": "contact-item-message"})
            ):
                continue
            last_msg_text = last_msg_text.text
            unread = True if "unread" in msg.get("class") else False
            chat_with = msg.find("div", {"class": "media-user-name"}).text
            node_msg_id = int(msg.get("data-node-msg"))
            user_msg_id = int(msg.get("data-user-msg"))
            by_bot = False
            by_vertex = False
            is_image = last_msg_text in ("Изображение", "Зображення", "Image")
            if last_msg_text.startswith(self.bot_character):
                last_msg_text = last_msg_text[1:]
                by_bot = True
            elif last_msg_text.startswith(self.old_bot_character):
                last_msg_text = last_msg_text[1:]
                by_vertex = True
            last_msg_text = strip_invisible_suffix(last_msg_text)
            chat_obj = types.ChatShortcut(
                chat_id,
                chat_with,
                last_msg_text,
                node_msg_id,
                user_msg_id,
                unread,
                str(msg),
            )
            if not is_image:
                chat_obj.last_by_bot = by_bot
                chat_obj.last_by_vertex = by_vertex
            chats_objs.append(chat_obj)
        return chats_objs

    def get_chats(self, update: bool = False) -> dict[int, types.ChatShortcut]:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if update:
            chats = self.request_chats()
            self.add_chats(chats)
        return self._Account__saved_chats

    def get_chat_by_name(
        self, name: str, make_request: bool = False
    ) -> types.ChatShortcut | None:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        for i in self._Account__saved_chats:
            if self._Account__saved_chats[i].name == name:
                return self._Account__saved_chats[i]
        if make_request:
            self.add_chats(self.request_chats())
            return self.get_chat_by_name(name)
        else:
            return None

    def get_chat_by_id(
        self, chat_id: int, make_request: bool = False
    ) -> types.ChatShortcut | None:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if not make_request or chat_id in self._Account__saved_chats:
            return self._Account__saved_chats.get(chat_id)
        self.add_chats(self.request_chats())
        return self.get_chat_by_id(chat_id)

    def calc(
        self,
        subcategory_type: enums.SubCategoryTypes,
        subcategory_id: int | None = None,
        game_id: int | None = None,
        price: int | float = 1000,
    ):
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if subcategory_type == types.SubCategoryTypes.COMMON:
            key = "nodeId"
            type_ = "lots"
            value = subcategory_id
        else:
            key = "game"
            type_ = "chips"
            value = game_id
        assert value is not None
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }
        r = self.method(
            "post",
            f"{type_}/calc",
            headers,
            {key: value, "price": price},
            raise_not_200=True,
        )
        json_resp = r.json()
        if error := json_resp.get("error"):
            raise Exception(f"Произошел бабах, не нашелся ответ: {error}")
        methods = []
        for method in json_resp.get("methods"):
            methods.append(
                PaymentMethod(
                    method.get("name"),
                    float(method["price"].replace(" ", "")),
                    parse_currency(method.get("unit")),
                    method.get("sort"),
                )
            )
        if "minPrice" in json_resp:
            min_price, min_price_currency = json_resp["minPrice"].rsplit(
                " ", maxsplit=1
            )
            min_price = float(min_price.replace(" ", ""))
            min_price_currency = parse_currency(min_price_currency)
        else:
            min_price, min_price_currency = (None, FunPayAPI.types.Currency.UNKNOWN)
        return CalcResult(
            subcategory_type,
            subcategory_id,
            methods,
            price,
            min_price,
            min_price_currency,
            self.currency,
        )

    def get_lot_fields(
        self, lot_id: int = 0, node_id: int | None = None
    ) -> types.LotFields:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        parameters = {}
        if lot_id:
            parameters["offer"] = lot_id
        if node_id:
            parameters["node"] = node_id
        response = self.method(
            "get",
            build_api_query("lots/offerEdit", parameters),
            {},
            {},
            raise_not_200=True,
        )
        return parse_lot_fields(self, response, lot_id)

    def get_chip_fields(self, subcategory_id: int) -> types.ChipFields:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        response = self.method(
            "get", f"chips/{subcategory_id}/trade", {}, {}, raise_not_200=True
        )
        return parse_chip_fields(self, response, subcategory_id)

    def save_offer(
        self,
        offer_fields: types.LotFields | types.ChipFields,
        locale: Literal["ru", "en", "uk"] | None = None,
    ):
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }
        offer_fields.csrf_token = self.csrf_token
        fields = offer_fields.renew_fields().fields
        if isinstance(offer_fields, types.LotFields):
            id_ = offer_fields.lot_id
            api_method = "lots/offerSave"
        else:
            id_ = offer_fields.subcategory_id
            api_method = "chips/saveOffers"
        response = self.method(
            "post", api_method, headers, fields, raise_not_200=True, locale=locale
        )
        json_response = response.json()
        errors_dict = {}
        if (errors := json_response.get("errors")) or json_response.get("error"):
            if errors:
                for k, v in errors:
                    errors_dict.update({k: v})
            raise exceptions.LotSavingError(
                response, json_response.get("error"), id_, errors_dict
            )

    def save_chip(
        self,
        chip_fields: types.ChipFields,
        locale: Literal["ru", "en", "uk"] | None = None,
    ):
        self.save_offer(chip_fields, locale)
