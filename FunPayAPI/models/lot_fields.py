from __future__ import annotations
import re
from FunPayAPI.common.enums import Currency
import FunPayAPI.types as _module_state


class LotField:
    def __init__(
        self,
        id: str,
        value: str | dict,
        name: str = None,
        field_type_id: str | None = None,
    ):
        self.id: str = id
        self.value: str | dict = value
        self.name: str = name
        self.field_type_id: str = field_type_id


class LotFields:
    def __init__(
        self,
        lot_id: int,
        fields: dict,
        subcategory: _module_state.SubCategory | None = None,
        currency: Currency = Currency.UNKNOWN,
        calc_result: _module_state.CalcResult | None = None,
        db_amount: int | None = None,
    ):
        self.lot_id: int = lot_id
        self.__fields: dict = fields
        self.title_ru: str = self.__fields.get("fields[summary][ru]", "")
        self.title_en: str = self.__fields.get("fields[summary][en]", "")
        self.description_ru: str = self.__fields.get("fields[desc][ru]", "")
        self.description_en: str = self.__fields.get("fields[desc][en]", "")
        self.payment_msg_ru: str = self.__fields.get("fields[payment_msg][ru]", "")
        self.payment_msg_en: str = self.__fields.get("fields[payment_msg][en]", "")
        self.images: list[int] = [
            int(i) for i in self.__fields.get("fields[images]", "").split(",") if i
        ]
        self.auto_delivery: bool | None = (
            bool(self.__fields["auto_delivery"])
            if "auto_delivery" in self.__fields
            else None
        )
        self.secrets: list[str] = [
            i for i in self.__fields.get("secrets", "").strip().split("\n") if i
        ]
        self._amount: int | None = self.__fields.get("amount")
        if self._amount is not None:
            self._amount = int(self._amount) if bool(self._amount) else 0
        self.price: float = float(i) if (i := self.__fields.get("price")) else None
        self.active: bool = (
            False if db_amount == 0 else self.__fields.get("active") == "on"
        )
        self.deactivate_after_sale: bool | None = (
            bool(self.__fields["deactivate_after_sale"])
            if "deactivate_after_sale" in self.__fields
            else None
        )
        self.subcategory: _module_state.SubCategory | None = subcategory
        self.currency: Currency = currency
        self.csrf_token: str | None = self.__fields.get("csrf_token")
        self.calc_result: _module_state.CalcResult | None = calc_result

    @property
    def amount(self) -> int | None:
        if self.auto_delivery:
            return len(self.secrets)
        return self._amount

    @amount.setter
    def amount(self, value: int | None):
        self._amount = value

    @property
    def public_link(self) -> str:
        return f"https://funpay.com/lots/offer?id={self.lot_id}"

    @property
    def private_link(self) -> str:
        return f"https://funpay.com/lots/offerEdit?offer={self.lot_id}"

    @property
    def fields(self) -> dict[str, str]:
        return self.__fields

    def edit_fields(self, fields: dict[str, str]):
        self.__fields.update(fields)

    def set_fields(self, fields: dict):
        self.__fields = fields

    def renew_fields(self) -> LotFields:
        self.__fields["offer_id"] = str(self.lot_id or 0)
        self.__fields["fields[summary][ru]"] = self.title_ru
        self.__fields["fields[summary][en]"] = self.title_en
        self.__fields["fields[desc][ru]"] = self.description_ru
        self.__fields["fields[desc][en]"] = self.description_en
        self.__fields["fields[payment_msg][ru]"] = self.payment_msg_ru
        self.__fields["fields[payment_msg][en]"] = self.payment_msg_en
        self.__fields["price"] = str(self.price) if self.price is not None else ""
        self.__fields["active"] = "on" if self.active else ""
        self.__fields["fields[images]"] = ",".join(map(str, self.images))
        self.__fields["secrets"] = "\n".join(self.secrets)
        self.__fields["csrf_token"] = self.csrf_token
        if self._amount is not None:
            self.__fields["amount"] = self._amount or ""
        else:
            self.__fields.pop("amount", None)
        if self.deactivate_after_sale is not None:
            self.__fields["deactivate_after_sale"] = (
                "on" if self.deactivate_after_sale else ""
            )
        else:
            self.__fields.pop("deactivate_after_sale", None)
        if self.auto_delivery is not None:
            self.__fields["auto_delivery"] = "on" if self.auto_delivery else ""
        else:
            self.__fields.pop("auto_delivery", None)
        return self


class ChipOffer:
    def __init__(
        self,
        lot_id: str,
        active: bool = False,
        server: str | None = None,
        side: str | None = None,
        price: float | None = None,
        amount: int | None = None,
    ):
        self.lot_id = lot_id
        self.active = active
        self.server = server
        self.side = side
        self.price = price
        self.amount = amount

    @property
    def key(self):
        s = "".join([f"[{i}]" for i in self.lot_id.split("-")[3:]])
        return f"offers{s}"


class ChipFields:
    def __init__(self, account_id: int, subcategory_id: int, fields: dict[str, str]):
        self.subcategory_id = subcategory_id
        self.__fields = fields
        self.min_sum = (
            float(i) if (i := self.__fields.get("options[chip_min_sum]")) else None
        )
        self.account_id: int = account_id
        self.game_id = int(self.__fields.get("game"))
        self.csrf_token: str | None = self.__fields.get("csrf_token")
        self.chip_offers: dict[str, _module_state.ChipOffer] = {}
        self.__parse_offers()

    @property
    def fields(self) -> dict[str, str]:
        return self.__fields

    def renew_fields(self) -> ChipFields:
        self.__fields["game"] = str(self.game_id)
        self.__fields["chip"] = str(self.subcategory_id)
        self.__fields["options[chip_min_sum]"] = (
            str(self.min_sum) if self.min_sum is not None else ""
        )
        self.__fields["csrf_token"] = self.csrf_token
        for chip_offer in self.chip_offers.values():
            key = chip_offer.key
            self.__fields[f"{key}[amount]"] = (
                str(chip_offer.amount) if chip_offer.amount is not None else ""
            )
            self.__fields[f"{key}[price]"] = (
                str(chip_offer.price) if chip_offer.price is not None else ""
            )
            if chip_offer.active:
                self.__fields[f"{key}[active]"] = "on"
            else:
                self.__fields.pop(f"{key}[active]", None)
        return self

    def __parse_offers(self):
        for k, v in self.__fields.items():
            if not k.startswith("offers"):
                continue
            nums = re.findall("\\d+", k)
            key = "-".join(list(map(str, nums)))
            offer_id = f"{self.account_id}-{self.game_id}-{self.subcategory_id}-{key}"
            if offer_id not in self.chip_offers:
                self.chip_offers[offer_id] = _module_state.ChipOffer(offer_id)
            chip_offer = self.chip_offers[offer_id]
            field = k.split("[")[-1].rstrip("]")
            if field == "active":
                chip_offer.active = v == "on"
            elif field == "price":
                chip_offer.price = float(v) if v else None
            elif field == "amount":
                chip_offer.amount = int(v) if v else None
