from __future__ import annotations
from typing import TYPE_CHECKING, Literal
from FunPayAPI.common.utils import parse_currency, RegularExpressions

if TYPE_CHECKING:
    pass
from bs4 import BeautifulSoup
import json
from FunPayAPI import types
from FunPayAPI.common import exceptions


class ProfileCatalog:
    def save_lot(
        self,
        lot_fields: types.LotFields,
        locale: Literal["ru", "en", "uk"] | None = None,
    ):
        self.save_offer(lot_fields, locale)

    def delete_lot(self, lot_id: int) -> None:
        self.save_lot(
            types.LotFields(
                lot_id,
                {"csrf_token": self.csrf_token, "offer_id": lot_id, "deleted": "1"},
            )
        )

    def get_exchange_rate(
        self, currency: types.Currency
    ) -> tuple[float, types.Currency]:
        r = self.method(
            "post",
            "https://funpay.com/account/switchCurrency",
            {
                "accept": "*/*",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "x-requested-with": "XMLHttpRequest",
            },
            {"cy": currency.code, "csrf_token": self.csrf_token, "confirmed": "false"},
            raise_not_200=True,
        )
        b = json.loads(r.text)
        if "url" in b and (not b["url"]):
            self.currency = currency
            return (1, currency)
        else:
            s = (
                BeautifulSoup(b["modal"], "lxml")
                .find("p", class_="lead")
                .text.replace("\xa0", " ")
            )
            match = RegularExpressions().EXCHANGE_RATE.fullmatch(s)
            assert match is not None
            swipe_to = match.group(2)
            assert swipe_to.lower() == currency.code
            price1 = float(match.group(4))
            currency1 = parse_currency(match.group(5))
            price2 = float(match.group(7))
            currency2 = parse_currency(match.group(8))
            now_currency = ({currency1, currency2} - {currency}).pop()
            self.currency = now_currency
            if now_currency == currency1:
                return (price2 / price1, now_currency)
            else:
                return (price1 / price2, now_currency)

    def get_buyer_viewing(self, buyer_id: int) -> types.BuyerViewing:
        json_result = self.abuse_runner(buyer_viewing_ids=[buyer_id]).json()
        for obj in json_result["objects"]:
            if obj["type"] != "c-p-u" or obj["id"] != int(buyer_id):
                continue
            return self._Account__parse_buyer_viewing(obj)
        return types.BuyerViewing(buyer_id, None, None, None, None)

    def get_buyers_viewing(self, *ids) -> dict[int, types.BuyerViewing]:
        json_result = self.abuse_runner(buyer_viewing_ids=list(ids)).json()
        result = {}
        for obj in json_result["objects"]:
            if obj["type"] != "c-p-u" or obj["id"] not in ids:
                continue
            result[obj["id"]] = self._Account__parse_buyer_viewing(obj)
        return result

    def get_wallets(self) -> list[types.Wallet]:
        response = self.method("get", "account/wallets", {}, {}, raise_not_200=True)
        bs = BeautifulSoup(response.content.decode(), "lxml")
        bs = bs.find("form", class_="details-editor")
        result = []
        for el in bs.find_all("div", class_="form-group"):
            data_n = int(el.get("data-n"))
            detail_id = int(
                el.find("input", {"name": f"details[{data_n}][detail_id]"})["value"]
            )
            if not detail_id:
                continue
            is_masked = bool(
                int(
                    el.find("input", {"name": f"details[{data_n}][is_masked]"})["value"]
                )
            )
            data = el.find("input", {"name": f"details[{data_n}][data]"})["value"]
            type_id = el.find("select", {"name": f"details[{data_n}][type_id]"}).find(
                "option", selected=True
            )
            result.append(
                types.Wallet(
                    type_id["value"], data, data_n, detail_id, is_masked, type_id.text
                )
            )
        return result

    def save_wallets(self, wallets: list[types.Wallet]):
        payload = {"csrf_token": self.csrf_token, "cat_id": "wallets"}
        max_n = max([i.data_n for i in wallets if i.data_n is not None], default=-1) + 1
        for wallet in wallets:
            if wallet.data_n is None:
                i = max_n
                max_n += 1
            else:
                i = wallet.data_n
            payload.update(
                {
                    f"details[{i}][detail_id]": wallet.detail_id or 0,
                    f"details[{i}][is_masked]": int(wallet.is_masked),
                }
            )
            if not wallet.is_masked:
                payload[f"details[{i}][type_id]"] = wallet.type_id
                payload[f"details[{i}][data]"] = wallet.data
        payload.update(
            {
                f"details[{max_n}][detail_id]": 0,
                f"details[{max_n}][is_masked]": 0,
                f"details[{max_n}][type_id]": "",
                f"details[{max_n}][data]": "",
            }
        )
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
        }
        r = self.method("post", "account/details", headers, payload, raise_not_200=True)
        if r.json().get("error"):
            raise Exception(r.json().get("msg"))

    def get_category(self, category_id: int) -> types.Category | None:
        return self._Account__sorted_categories.get(category_id)

    @property
    def categories(self) -> list[types.Category]:
        return self._Account__categories

    def get_sorted_categories(self) -> dict[int, types.Category]:
        return self._Account__sorted_categories

    def get_subcategory(
        self, subcategory_type: types.SubCategoryTypes, subcategory_id: int
    ) -> types.SubCategory | None:
        return self._Account__sorted_subcategories[subcategory_type].get(subcategory_id)

    @property
    def subcategories(self) -> list[types.SubCategory]:
        return self._Account__subcategories

    def get_sorted_subcategories(
        self,
    ) -> dict[types.SubCategoryTypes, dict[int, types.SubCategory]]:
        return self._Account__sorted_subcategories

    def logout(self) -> None:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        self.method("get", self._logout_link, {"accept": "*/*"}, {}, raise_not_200=True)

    @property
    def is_initiated(self) -> bool:
        return self._Account__initiated

    def _Account__setup_categories(self, html: str):
        parser = BeautifulSoup(html, "lxml")
        games_table = parser.find_all("div", {"class": "promo-game-list"})
        if not games_table:
            return
        games_table = games_table[1] if len(games_table) > 1 else games_table[0]
        games_divs = games_table.find_all("div", {"class": "promo-game-item"})
        if not games_divs:
            return
        game_position = 0
        subcategory_position = 0
        for i in games_divs:
            gid = int(i.find("div", {"class": "game-title"}).get("data-id"))
            gname = i.find("a").text
            regional_games = {gid: types.Category(gid, gname, position=game_position)}
            game_position += 1
            if regional_divs := i.find("div", {"role": "group"}):
                for btn in regional_divs.find_all("button"):
                    regional_game_id = int(btn["data-id"])
                    regional_games[regional_game_id] = types.Category(
                        regional_game_id,
                        f"{gname} ({btn.text})",
                        position=game_position,
                    )
                    game_position += 1
            subcategories_divs = i.find_all("ul", {"class": "list-inline"})
            for j in subcategories_divs:
                j_game_id = int(j["data-id"])
                subcategories = j.find_all("li")
                for k in subcategories:
                    a = k.find("a")
                    name, link = (a.text, a["href"])
                    stype = (
                        types.SubCategoryTypes.CURRENCY
                        if "chips" in link
                        else types.SubCategoryTypes.COMMON
                    )
                    sid = int(link.split("/")[-2])
                    sobj = types.SubCategory(
                        sid,
                        name,
                        stype,
                        regional_games[j_game_id],
                        subcategory_position,
                    )
                    subcategory_position += 1
                    regional_games[j_game_id].add_subcategory(sobj)
                    self._Account__subcategories.append(sobj)
                    self._Account__sorted_subcategories[stype][sid] = sobj
            for gid in regional_games:
                self._Account__categories.append(regional_games[gid])
                self._Account__sorted_categories[gid] = regional_games[gid]
