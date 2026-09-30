from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Optional
import FunPayAPI.common.enums
from FunPayAPI.common.utils import parse_currency

if TYPE_CHECKING:
    pass
from bs4 import BeautifulSoup
import json
from FunPayAPI import types
from FunPayAPI.common import exceptions, utils
from FunPayAPI.accounts.sales_filters import is_sales_heading
from FunPayAPI.accounts.chat_context import chat_page_details
from FunPayAPI.accounts.constants import CHAT_PAGE_PATH
from FunPayAPI.security.constants import SALES_PATH, XHR_FORM_HEADERS
from FunPayAPI.security.urls import build_api_query


class OrderQueries:
    def get_chat(
        self,
        chat_id: int,
        with_history: bool = True,
        locale: Literal["ru", "en", "uk"] | None = None,
    ) -> types.Chat:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        locale = locale or self._Account__chat_parse_locale
        response = self.method(
            "get",
            build_api_query(CHAT_PAGE_PATH, {"node": chat_id}),
            {"accept": "*/*"},
            {},
            raise_not_200=True,
            locale=locale,
        )
        if locale:
            self.locale = self._Account__default_locale
        document = response.content.decode()
        parser = BeautifulSoup(document, "lxml")
        name, text, link = chat_page_details(parser)
        self._Account__update_csrf_token(parser)
        history = (
            self.get_chats_histories({chat_id: name}).get(chat_id, [])
            if with_history
            else []
        )
        return types.Chat(chat_id, name, link, text, document, history)

    def get_order_shortcut(self, order_id: str) -> types.OrderShortcut:
        saved_orders = self.runner.saved_orders if self.runner else None
        if saved_orders is not None and order_id in saved_orders:
            return saved_orders[order_id]
        orders = self.get_sales(id=order_id)[1]
        if not orders:
            raise LookupError("Order not found in sales")
        return orders[0]

    def get_orders_by_ids(
        self,
        *order_ids: str,
        include_details: bool = True,
        include_users: bool = True,
        include_review: bool = True,
        locale: Literal["ru", "en", "uk"] | None = None,
    ) -> dict[str, FunPayAPI.types.Order]:
        if not 1 <= len(order_ids) <= 10:
            raise ValueError("order_ids must contain 1–10 items")
        include = []
        if include_details:
            include.append("details")
        if include_users:
            include.append("users")
        if include_review:
            include.append("review")
        headers = {"Content-Type": "application/json"}
        locale = locale or self._Account__order_parse_locale or self.locale or "ru"
        headers["Accept-Language"] = locale
        payload = {"order_uids": list(order_ids), "include": include}
        r = self.method(
            "post",
            "https://funpay.com/api/orders/get",
            headers=headers,
            payload=json.dumps(payload),
            raise_not_200=True,
        )
        d = r.json()
        if d.get("status") != "SUCCESS" or "data" not in d:
            raise exceptions.RequestFailedError(response=r)
        return {
            order_id: self._Account__parse_order(order_data, locale)
            for order_id, order_data in d.get("data").items()
        }

    def get_order(
        self,
        order_id: str,
        include_details: bool = True,
        include_users: bool = True,
        include_review: bool = True,
        locale: Literal["ru", "en", "uk"] | None = None,
    ) -> types.Order:
        return self.get_orders_by_ids(
            order_id,
            include_users=include_users,
            include_details=include_details,
            include_review=include_review,
            locale=locale,
        )[order_id]

    def get_sales(
        self,
        start_from: str | None = None,
        include_paid: bool = True,
        include_closed: bool = True,
        include_refunded: bool = True,
        exclude_ids: list[str] | None = None,
        id: Optional[str] = None,
        buyer: Optional[str] = None,
        state: Optional[Literal["closed", "paid", "refunded"]] = None,
        game: Optional[int] = None,
        section: Optional[str] = None,
        server: Optional[int] = None,
        side: Optional[int] = None,
        locale: Literal["ru", "en", "uk"] | None = None,
        subcategories: dict[str, tuple[types.SubCategoryTypes, int]] | None = None,
        **more_filters,
    ) -> tuple[
        str | None,
        list[types.OrderShortcut],
        Literal["ru", "en", "uk"],
        dict[str, types.SubCategory],
    ]:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        exclude_ids = exclude_ids or []
        _subcategories = more_filters.pop("sudcategories", None)
        subcategories = subcategories or _subcategories
        filters = {
            "id": id,
            "buyer": buyer,
            "state": state,
            "game": game,
            "section": section,
            "server": server,
            "side": side,
        }
        filters = {
            name: value
            for name, value in filters.items()
            if value is not None and value != ""
        }
        filters.update(more_filters)
        link = build_api_query(SALES_PATH, filters)
        if start_from:
            filters["continue"] = start_from
        locale = locale or self._Account__profile_parse_locale
        response = self.method(
            "post" if start_from else "get",
            link,
            dict(XHR_FORM_HEADERS) if start_from else {},
            filters if start_from else {},
            raise_not_200=True,
            locale=locale,
        )
        if not start_from:
            self.locale = self._Account__default_locale
        html_response = response.content.decode()
        parser = BeautifulSoup(html_response, "lxml")
        if not start_from:
            username = parser.find("div", {"class": "user-link-name"})
            if not username:
                raise exceptions.UnauthorizedError(response)
            header = parser.select_one("h1.page-header.page-header-no-hr")
            if not is_sales_heading(header):
                raise exceptions.UnauthorizedError(response)
        next_order_id = parser.find("input", {"type": "hidden", "name": "continue"})
        next_order_id = next_order_id.get("value") if next_order_id else None
        order_divs = parser.find_all("a", {"class": "tc-item"})
        if not start_from:
            subcategories = dict()
            app_data = json.loads(parser.find("body").get("data-app-data"))
            locale = app_data.get("locale")
            self.csrf_token = app_data.get("csrf-token") or self.csrf_token
            games_options = parser.find("select", attrs={"name": "game"})
            if games_options:
                games_options = games_options.find_all(
                    lambda x: x.name == "option" and x.get("value")
                )
                for game_option in games_options:
                    game_name = game_option.text
                    sections_list = json.loads(game_option.get("data-data"))
                    for key, section_name in sections_list:
                        section_type, section_id = key.split("-")
                        section_type = (
                            types.SubCategoryTypes.COMMON
                            if section_type == "lot"
                            else types.SubCategoryTypes.CURRENCY
                        )
                        section_id = int(section_id)
                        subcategories[f"{game_name}, {section_name}"] = (
                            self.get_subcategory(section_type, section_id)
                        )
            else:
                subcategories = None
        if not order_divs:
            return (None, [], locale, subcategories)
        sales = []
        for div in order_divs:
            classname = div.get("class")
            if "warning" in classname:
                if not include_refunded:
                    continue
                order_status = types.OrderStatuses.REFUNDED
            elif "info" in classname:
                if not include_paid:
                    continue
                order_status = types.OrderStatuses.PAID
            else:
                if not include_closed:
                    continue
                order_status = types.OrderStatuses.CLOSED
            order_id = div.find("div", {"class": "tc-order"}).text[1:]
            if order_id in exclude_ids:
                continue
            description = div.find("div", {"class": "order-desc"}).find("div").text
            tc_price = div.find("div", {"class": "tc-price"}).text
            price, currency = tc_price.rsplit(maxsplit=1)
            price = float(price.replace(" ", ""))
            currency = parse_currency(currency)
            buyer_div = div.find("div", {"class": "media-user-name"}).find("span")
            buyer_username = buyer_div.text
            buyer_id = int(buyer_div.get("data-href")[:-1].split("/users/")[1])
            subcategory_name = div.find("div", {"class": "text-muted"}).text
            subcategory = None
            if subcategories:
                subcategory = subcategories.get(subcategory_name)
            order_date_text = div.find("div", {"class": "tc-date-time"}).text
            order_date = utils.parse_funpay_datetime(order_date_text)
            id1, id2 = sorted([buyer_id, self.id])
            chat_id = f"users-{id1}-{id2}"
            order_obj = types.OrderShortcut(
                order_id,
                description,
                price,
                currency,
                buyer_username,
                buyer_id,
                chat_id,
                order_status,
                order_date,
                subcategory_name,
                subcategory,
                str(div),
            )
            sales.append(order_obj)
        return (next_order_id, sales, locale, subcategories)

    def get_sells(
        self,
        start_from: str | None = None,
        include_paid: bool = True,
        include_closed: bool = True,
        include_refunded: bool = True,
        exclude_ids: list[str] | None = None,
        id: Optional[str] = None,
        buyer: Optional[str] = None,
        state: Optional[Literal["closed", "paid", "refunded"]] = None,
        game: Optional[int] = None,
        section: Optional[str] = None,
        server: Optional[int] = None,
        side: Optional[int] = None,
        **more_filters,
    ) -> tuple[str | None, list[types.OrderShortcut]]:
        start_from, orders, loc, subcs = self.get_sales(
            start_from,
            include_paid,
            include_closed,
            include_refunded,
            exclude_ids,
            id,
            buyer,
            state,
            game,
            section,
            server,
            side,
            None,
            None,
            **more_filters,
        )
        return (start_from, orders)

    def add_chats(self, chats: list[types.ChatShortcut]):
        for i in chats:
            self._Account__saved_chats[i.id] = i
