from __future__ import annotations
from typing import Literal
from FunPayAPI.common.enums import OrderStatuses, SubCategoryTypes, Currency
import FunPayAPI.types as _module_state


class Side:
    def __init__(self, id_: int, name: str | None = None):
        self.id: int = id_
        self.name = name


class Order:
    def __init__(
        self,
        id_: str,
        status: OrderStatuses,
        subcategory: SubCategory | None,
        server: _module_state.Server | None,
        side: Side | None,
        fields: dict[str, _module_state.LotField],
        amount: int,
        sum_: float,
        currency: Currency,
        player: str | None,
        buyer_id: int,
        buyer_username: str | None,
        seller_id: int,
        seller_username: str | None,
        chat_id: str | int,
        review: _module_state.Review | None,
        order_secrets: list[str],
        locale: Literal["ru", "en", "uk"],
    ):
        self.id: str = id_ if not id_.startswith("#") else id_[1:]
        self.status: OrderStatuses = status
        self.subcategory: _module_state.SubCategory | None = subcategory
        self.fields: dict[str, _module_state.LotField] = fields
        self.sum: float = sum_
        self.currency: Currency = currency
        self.buyer_id: int = buyer_id
        self.buyer_username: str | None = buyer_username
        self.seller_id: int = seller_id
        self.seller_username: str | None = seller_username
        self.chat_id: str | int = chat_id
        self.review: _module_state.Review | None = review
        self.amount: int = amount
        self.locale: Literal["ru", "en"] = "en" if locale == "en" else "ru"
        self.player: str | None = player
        self.server: _module_state.Server | None = server
        self.side: _module_state.Side | None = side
        self.order_secrets: list[str] = order_secrets

    def get_field(self, key: str) -> _module_state.LotField | None:
        return self.fields.get(key)

    def get_field_value(
        self, key: str, locale: Literal["ru", "en"] = "ru"
    ) -> str | None:
        field = self.get_field(key)
        if not field:
            return None
        if isinstance(field.value, dict):
            return field.value.get(locale)
        return field.value

    def get_field_value_any(self, key: str) -> str | None:
        locales = [self.locale] + [l for l in ("ru", "en") if l != self.locale]
        for locale in locales:
            value = self.get_field_value(key, locale)
            if value:
                return value
        return None

    @property
    def short_description(self) -> str | None:
        return self.get_field_value_any("summary")

    @property
    def title(self) -> str:
        return self.short_description

    @property
    def full_description(self) -> str:
        return self.get_field_value_any("desc")

    @property
    def payment_msg(self) -> str:
        return self.get_field_value_any("payment_msg")

    @property
    def lot_params(self) -> list[tuple[str, str]]:
        result = []
        for key, field in self.fields.items():
            if key in ("payment_msg", "desc", "summary"):
                continue
            v = self.get_field_value_any(key)
            result.append((field.name, v))
        return result

    @property
    def lot_params_text(self) -> str | None:
        result = None
        for key, field in self.fields.items():
            if key in ("payment_msg", "desc", "summary"):
                continue
            v = self.get_field_value_any(key)
            if not v:
                continue
            s = f"{v} {field.name}" if isinstance(v, int) or str(v).isdigit() else v
            result = f"{result}, {s}" if result else s
        return result

    @property
    def lot_params_dict(self) -> dict[str, str]:
        d = {}
        for key, field in self.fields.items():
            if key in ("payment_msg", "desc", "summary"):
                continue
            d[field.name] = self.get_field_value_any(key)
        return d

    @property
    def character_name(self) -> str | None:
        return self.player

    def __str__(self):
        return f"#{self.id}"


class Category:
    def __init__(
        self,
        id_: int,
        name: str,
        subcategories: list[SubCategory] | None = None,
        position: int = 100000,
    ):
        self.id: int = id_
        self.name: str = name
        self.__subcategories: list[_module_state.SubCategory] = subcategories or []
        self.position = position
        self.__sorted_subcategories: dict[
            SubCategoryTypes, dict[int, _module_state.SubCategory]
        ] = {SubCategoryTypes.COMMON: {}, SubCategoryTypes.CURRENCY: {}}
        for i in self.__subcategories:
            self.__sorted_subcategories[i.type][i.id] = i

    def add_subcategory(self, subcategory: SubCategory):
        if subcategory not in self.__subcategories:
            self.__subcategories.append(subcategory)
            self.__sorted_subcategories[subcategory.type][subcategory.id] = subcategory

    def get_subcategory(
        self, subcategory_type: SubCategoryTypes, subcategory_id: int
    ) -> SubCategory | None:
        return self.__sorted_subcategories[subcategory_type].get(subcategory_id)

    def get_subcategories(self) -> list[SubCategory]:
        return self.__subcategories

    def get_sorted_subcategories(
        self,
    ) -> dict[SubCategoryTypes, dict[int, SubCategory]]:
        return self.__sorted_subcategories


class SubCategory:
    def __init__(
        self,
        id_: int,
        name: str,
        type_: SubCategoryTypes,
        category: Category,
        position: int = 100000,
    ):
        self.id: int = id_
        self.name: str = name
        self.type: SubCategoryTypes = type_
        self.category: _module_state.Category = category
        self.position: int = position
        self.fullname: str = f"{self.name} {self.category.name}"
        self.public_link: str = (
            f"https://funpay.com/chips/{id_}/"
            if type_ is SubCategoryTypes.CURRENCY
            else f"https://funpay.com/lots/{id_}/"
        )
        self.private_link: str = f"{self.public_link}trade"

    @property
    def is_common(self):
        return self.type == SubCategoryTypes.COMMON

    @property
    def is_lots(self):
        return self.is_common

    @property
    def is_currency(self):
        return self.type == SubCategoryTypes.CURRENCY

    @property
    def is_chips(self):
        return self.is_currency

    @property
    def ui_name(self):
        return f"{self.category.name} / {self.name}"

    def telegram_text(self, link: Literal["private", "public", None] = None) -> str:
        if link == "private":
            return f"<a href='{self.private_link}'>{self.ui_name}</a>"
        if link == "public":
            return f"<a href='{self.public_link}'>{self.ui_name}</a>"
        return self.ui_name
