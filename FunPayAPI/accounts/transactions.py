from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Optional
from FunPayAPI.common.utils import parse_currency

if TYPE_CHECKING:
    pass
from bs4 import BeautifulSoup
from FunPayAPI import types
from FunPayAPI.accounts.public_offers import public_offer_id
from FunPayAPI.common import exceptions, utils, enums
import FunPayAPI.account as _module_state


class Transactions:
    def send_review(
        self, order_id: str, text: str, rating: Literal[1, 2, 3, 4, 5] = 5
    ) -> str:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {"accept": "*/*", "x-requested-with": "XMLHttpRequest"}
        text = text.strip()
        payload = {
            "authorId": self.id,
            "text": f"{text}{self._Account__bot_character}" if text else text,
            "rating": rating or "",
            "csrf_token": self.csrf_token,
            "orderId": order_id,
        }
        response = self.method("post", "orders/review", headers, payload)
        if response.status_code == 400:
            json_response = response.json()
            msg = json_response.get("msg")
            raise exceptions.FeedbackEditingError(response, msg, order_id)
        elif response.status_code != 200:
            raise exceptions.RequestFailedError(response)
        return response.json().get("content")

    def delete_review(self, order_id: str) -> str:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {"accept": "*/*", "x-requested-with": "XMLHttpRequest"}
        payload = {
            "authorId": self.id,
            "csrf_token": self.csrf_token,
            "orderId": order_id,
        }
        response = self.method("post", "orders/reviewDelete", headers, payload)
        if response.status_code == 400:
            json_response = response.json()
            msg = json_response.get("msg")
            raise exceptions.FeedbackEditingError(response, msg, order_id)
        elif response.status_code != 200:
            raise exceptions.RequestFailedError(response)
        return response.json().get("content")

    def refund(self, order_id):
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }
        payload = {"id": order_id, "csrf_token": self.csrf_token}
        response = self.method(
            "post", "orders/refund", headers, payload, raise_not_200=True
        )
        if response.json().get("error"):
            raise exceptions.RefundError(response, response.json().get("msg"), order_id)

    def withdraw(
        self,
        currency: enums.Currency,
        wallet: enums.Wallet,
        amount: int | float,
        address: str,
    ) -> float:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        wallets = {
            enums.Wallet.QIWI: "qiwi",
            enums.Wallet.YOUMONEY: "fps",
            enums.Wallet.BINANCE: "binance",
            enums.Wallet.TRC: "usdt_trc",
            enums.Wallet.CARD_RUB: "card_rub",
            enums.Wallet.CARD_USD: "card_usd",
            enums.Wallet.CARD_EUR: "card_eur",
            enums.Wallet.WEBMONEY: "wmz",
        }
        headers = {"accept": "*/*", "x-requested-with": "XMLHttpRequest"}
        payload = {
            "csrf_token": self.csrf_token,
            "currency_id": currency.code,
            "ext_currency_id": wallets[wallet],
            "wallet": address,
            "amount_int": str(amount),
        }
        response = self.method(
            "post", "withdraw/withdraw", headers, payload, raise_not_200=True
        )
        json_response = response.json()
        if json_response.get("error"):
            error_message = json_response.get("msg")
            raise exceptions.WithdrawError(response, error_message)
        return float(json_response.get("amount_ext"))

    def get_raise_modal(self, category_id: int) -> dict:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        category = self.get_category(category_id)
        subcategory = category.get_subcategories()[0]
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }
        payload = {"game_id": category_id, "node_id": subcategory.id}
        response = self.method(
            "post",
            "https://funpay.com/lots/raise",
            headers,
            payload,
            raise_not_200=True,
        )
        json_response = response.json()
        return json_response

    def raise_lots(
        self,
        category_id: int,
        subcategories: Optional[list[int | types.SubCategory]] = None,
        exclude: list[int] | None = None,
    ) -> int:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if not (category := self.get_category(category_id)):
            raise Exception("Not Found")
        exclude = exclude or []
        if subcategories:
            subcats = []
            for i in subcategories:
                if isinstance(i, types.SubCategory):
                    if (
                        i.type is types.SubCategoryTypes.COMMON
                        and i.category.id == category.id
                        and (i.id not in exclude)
                    ):
                        subcats.append(i)
                else:
                    if not (
                        subcat := category.get_subcategory(
                            types.SubCategoryTypes.COMMON, i
                        )
                    ):
                        continue
                    subcats.append(subcat)
        else:
            subcats = [
                i
                for i in category.get_subcategories()
                if i.type is types.SubCategoryTypes.COMMON and i.id not in exclude
            ]
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }
        payload = {
            "game_id": category_id,
            "node_id": subcats[0].id,
            "node_ids[]": [i.id for i in subcats],
        }
        response = self.method(
            "post", "lots/raise", headers, payload, raise_not_200=True
        )
        json_response = response.json()
        _module_state.logger.debug(
            f"Ответ FunPay (поднятие категорий): {json_response}."
        )
        wait_time = json_response.get("wait")
        if not json_response.get("error") and (not json_response.get("url")):
            return wait_time
        elif json_response.get("url"):
            raise exceptions.RaiseError(
                response, category, json_response.get("url"), wait_time or 7200
            )
        elif (
            json_response.get("error")
            and json_response.get("msg")
            and any(
                [
                    i in json_response.get("msg")
                    for i in ("Подождите ", "Please wait ", "Зачекайте ")
                ]
            )
        ):
            raise exceptions.RaiseError(
                response,
                category,
                json_response.get("msg"),
                wait_time or utils.parse_wait_time(json_response.get("msg")),
            )
        else:
            raise exceptions.RaiseError(
                response, category, json_response.get("msg"), wait_time
            )

    def get_user(
        self, user_id: int, locale: Literal["ru", "en", "uk"] | None = None
    ) -> types.UserProfile:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if not locale:
            locale = self._Account__profile_parse_locale
        response = self.method(
            "get",
            f"users/{user_id}/",
            {"accept": "*/*"},
            {},
            raise_not_200=True,
            locale=locale,
        )
        if locale:
            self.locale = self._Account__default_locale
        html_response = response.content.decode()
        parser = BeautifulSoup(html_response, "lxml")
        username = parser.find("div", {"class": "user-link-name"})
        if not username:
            raise exceptions.UnauthorizedError(response)
        self._Account__update_csrf_token(parser)
        username = parser.find("span", {"class": "mr4"}).text
        user_status = parser.find("span", {"class": "media-user-status"})
        user_status = user_status.text if user_status else ""
        avatar_link = (
            parser.find("div", {"class": "avatar-photo"})
            .get("style")
            .split("(")[1]
            .split(")")[0]
        )
        avatar_link = (
            avatar_link
            if avatar_link.startswith("https")
            else f"https://funpay.com{avatar_link}"
        )
        banned = bool(parser.find("span", {"class": "label label-danger"}))
        user_obj = types.UserProfile(
            user_id,
            username,
            avatar_link,
            "Онлайн" in user_status or "Online" in user_status,
            banned,
            html_response,
        )
        subcategories_divs = parser.find_all(
            "div", {"class": "offer-list-title-container"}
        )
        if not subcategories_divs:
            return user_obj
        for i in subcategories_divs:
            subcategory_link = i.find("h3").find("a").get("href")
            subcategory_id = int(subcategory_link.split("/")[-2])
            subcategory_type = (
                types.SubCategoryTypes.CURRENCY
                if "chips" in subcategory_link
                else types.SubCategoryTypes.COMMON
            )
            subcategory_obj = self.get_subcategory(subcategory_type, subcategory_id)
            if not subcategory_obj:
                continue
            offers = i.parent.find_all("a", {"class": "tc-item"})
            currency = None
            for j in offers:
                offer_id = public_offer_id(j["href"])
                description = j.find("div", {"class": "tc-desc-text"})
                description = description.text if description else None
                server = j.find("div", class_="tc-server")
                server = server.text if server else None
                side = j.find("div", class_="tc-side")
                side = side.text if side else None
                auto = j.find("i", class_="auto-dlv-icon") is not None
                tc_price = j.find("div", {"class": "tc-price"})
                tc_amount = j.find("div", class_="tc-amount")
                amount = tc_amount.text.replace(" ", "") if tc_amount else None
                amount = int(amount) if amount and amount.isdigit() else None
                if subcategory_obj.type is types.SubCategoryTypes.COMMON:
                    price = float(tc_price["data-s"])
                else:
                    price = float(
                        tc_price.find("div").text.rsplit(maxsplit=1)[0].replace(" ", "")
                    )
                if currency is None:
                    currency = parse_currency(tc_price.find("span", class_="unit").text)
                    if self.currency != currency:
                        self.currency = currency
                lot_obj = types.LotShortcut(
                    offer_id,
                    server,
                    side,
                    description,
                    amount,
                    price,
                    currency,
                    subcategory_obj,
                    None,
                    auto,
                    None,
                    None,
                    str(j),
                )
                user_obj.add_lot(lot_obj)
        return user_obj
