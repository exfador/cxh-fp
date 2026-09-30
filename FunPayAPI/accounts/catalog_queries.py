from __future__ import annotations
from typing import TYPE_CHECKING, Literal
from FunPayAPI.common.utils import parse_currency

if TYPE_CHECKING:
    pass
from bs4 import BeautifulSoup
from FunPayAPI import types
from FunPayAPI.accounts.public_offers import parse_lot_page
from FunPayAPI.accounts.public_catalog import parse_public_catalog
from FunPayAPI.security.urls import build_api_query
from FunPayAPI.common import exceptions, enums


class CatalogQueries:
    def get_subcategory_public_lots(
        self,
        subcategory_type: enums.SubCategoryTypes,
        subcategory_id: int,
        locale: Literal["ru", "en", "uk"] | None = None,
    ) -> list[types.LotShortcut]:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        section = (
            "lots" if subcategory_type is enums.SubCategoryTypes.COMMON else "chips"
        )
        locale = locale or self._Account__lots_parse_locale
        response = self.method(
            "get",
            f"{section}/{subcategory_id}/",
            {"accept": "*/*"},
            {},
            raise_not_200=True,
            locale=locale,
        )
        if locale:
            self.locale = self._Account__default_locale
        parser = BeautifulSoup(response.content.decode(), "lxml")
        if not parser.find("div", class_="user-link-name"):
            raise exceptions.UnauthorizedError(response)
        result = parse_public_catalog(self, parser, subcategory_type, subcategory_id)
        self._Account__update_csrf_token(parser)
        return result

    def get_my_subcategory_lots(
        self, subcategory_id: int, locale: Literal["ru", "en", "uk"] | None = None
    ) -> list[types.MyLotShortcut]:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        meth = f"lots/{subcategory_id}/trade"
        if not locale:
            locale = self._Account__lots_parse_locale
        response = self.method(
            "get", meth, {"accept": "*/*"}, {}, raise_not_200=True, locale=locale
        )
        if locale:
            self.locale = self._Account__default_locale
        html_response = response.content.decode()
        parser = BeautifulSoup(html_response, "lxml")
        username = parser.find("div", {"class": "user-link-name"})
        if not username:
            raise exceptions.UnauthorizedError(response)
        self._Account__update_csrf_token(parser)
        offers = parser.find_all("a", class_="tc-item")
        if not offers:
            return []
        subcategory_obj = self.get_subcategory(
            enums.SubCategoryTypes.COMMON, subcategory_id
        )
        result = []
        currency = None
        for offer in offers:
            offer_id = offer["data-offer"]
            description = offer.find("div", {"class": "tc-desc-text"})
            description = description.text if description else None
            server = offer.find("div", class_="tc-server")
            server = server.text if server else None
            side = offer.find("div", class_="tc-side")
            side = side.text if side else None
            tc_price = offer.find("div", class_="tc-price")
            price = float(tc_price["data-s"])
            if currency is None:
                currency = parse_currency(tc_price.find("span", class_="unit").text)
                if self.currency != currency:
                    self.currency = currency
            auto = bool(tc_price.find("i", class_="auto-dlv-icon"))
            tc_amount = offer.find("div", class_="tc-amount")
            amount = tc_amount.text.replace(" ", "") if tc_amount else None
            amount = int(amount) if amount and amount.isdigit() else None
            active = "warning" not in offer.get("class", [])
            lot_obj = types.MyLotShortcut(
                offer_id,
                server,
                side,
                description,
                amount,
                price,
                currency,
                subcategory_obj,
                auto,
                active,
                str(offer),
            )
            result.append(lot_obj)
        return result

    def get_lot_page(
        self, lot_id: int, locale: Literal["ru", "en", "uk"] | None = None
    ):
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        response = self.method(
            "get",
            build_api_query("lots/offer", {"id": lot_id}),
            {"accept": "*/*"},
            {},
            raise_not_200=True,
            locale=locale,
        )
        if locale:
            self.locale = self._Account__default_locale
        parser = BeautifulSoup(response.content.decode(), "lxml")
        if not parser.find("div", class_="user-link-name"):
            raise exceptions.UnauthorizedError(response)
        self._Account__update_csrf_token(parser)
        return parse_lot_page(self, parser, lot_id)
