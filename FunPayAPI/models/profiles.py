from __future__ import annotations
from typing import Literal, overload
from FunPayAPI.common.enums import SubCategoryTypes, Currency
import FunPayAPI.types as _module_state


class LotPage:
    def __init__(
        self,
        lot_id: int,
        subcategory: _module_state.SubCategory | None,
        short_description: str | None,
        full_description: str | None,
        image_urls: list[str],
        seller_id: int,
        seller_username: str,
    ) -> None:
        self.lot_id: int = lot_id
        self.subcategory: _module_state.SubCategory | None = subcategory
        self.short_description: str | None = short_description
        self.full_description: str | None = full_description
        self.image_urls = image_urls
        self.seller_id: int = seller_id
        self.seller_username: str = seller_username

    @property
    def seller_url(self) -> str:
        return f"https://funpay.com/users/{self.seller_id}/"


class SellerShortcut:
    def __init__(
        self,
        id_: int,
        username: str,
        online: bool,
        stars: None | int,
        reviews: int,
        html: str,
    ):
        self.id: int = id_
        self.username: str = username
        self.online: bool = online
        self.stars: int | None = stars
        self.reviews: int = reviews
        self.html: str = html

    @property
    def link(self):
        return f"https://funpay.com/users/{self.id}/"


class LotShortcut:
    def __init__(
        self,
        id_: int | str,
        server: str | None,
        side: str | None,
        description: str | None,
        amount: int | None,
        price: float,
        currency: Currency,
        subcategory: _module_state.SubCategory | None,
        seller: SellerShortcut | None,
        auto: bool,
        promo: bool | None,
        attributes: dict[str, int | str] | None,
        html: str,
    ):
        self.id: int | str = id_
        if isinstance(self.id, str) and self.id.isnumeric():
            self.id = int(self.id)
        self.server: str | None = server
        self.side: str | None = side
        self.description: str | None = description
        self.title: str | None = description
        self.amount: int | None = amount
        self.price: float = price
        self.currency: Currency = currency
        self.seller: _module_state.SellerShortcut | None = seller
        self.auto: bool = auto
        self.promo: bool | None = promo
        self.attributes: dict[str, int | str] | None = attributes
        self.subcategory: _module_state.SubCategory = subcategory
        self.html: str = html
        self.public_link: str = (
            f"https://funpay.com/chips/offer?id={self.id}"
            if self.subcategory.type is SubCategoryTypes.CURRENCY
            else f"https://funpay.com/lots/offer?id={self.id}"
        )


class MyLotShortcut:
    def __init__(
        self,
        id_: int | str,
        server: str | None,
        side: str | None,
        description: str | None,
        amount: int | None,
        price: float,
        currency: Currency,
        subcategory: _module_state.SubCategory | None,
        auto: bool,
        active: bool,
        html: str,
    ):
        self.id: int | str = id_
        if isinstance(self.id, str) and self.id.isnumeric():
            self.id = int(self.id)
        self.server: str | None = server
        self.side: str | None = side
        self.description: str | None = description
        self.title: str | None = description
        self.amount: int | None = amount
        self.price: float = price
        self.currency: Currency = currency
        self.auto: bool = auto
        self.subcategory: _module_state.SubCategory = subcategory
        self.active: bool = active
        self.html: str = html
        self.public_link: str = (
            f"https://funpay.com/chips/offer?id={self.id}"
            if self.subcategory.type is SubCategoryTypes.CURRENCY
            else f"https://funpay.com/lots/offer?id={self.id}"
        )


class UserProfile:
    def __init__(
        self,
        id_: int,
        username: str,
        profile_photo: str,
        online: bool,
        banned: bool,
        html: str,
    ):
        self.id: int = id_
        self.username: str = username
        self.profile_photo: str = profile_photo
        self.online: bool = online
        self.banned: bool = banned
        self.html: str = html
        self.__lots_ids: dict[int | str, _module_state.LotShortcut] = {}
        self.__sorted_by_subcategory_lots: dict[
            _module_state.SubCategory, dict[int | str, _module_state.LotShortcut]
        ] = {}
        self.__sorted_by_subcategory_type_lots: dict[
            SubCategoryTypes, dict[int | str, _module_state.LotShortcut]
        ] = {SubCategoryTypes.COMMON: {}, SubCategoryTypes.CURRENCY: {}}

    def get_lot(self, lot_id: int | str) -> LotShortcut | None:
        if isinstance(lot_id, str) and lot_id.isnumeric():
            return self.__lots_ids.get(int(lot_id))
        return self.__lots_ids.get(lot_id)

    def get_lots(self) -> list[LotShortcut]:
        return list(self.__lots_ids.values())

    @overload
    def get_sorted_lots(self, mode: Literal[1]) -> dict[int | str, LotShortcut]: ...

    @overload
    def get_sorted_lots(
        self, mode: Literal[2]
    ) -> dict[_module_state.SubCategory, dict[int | str, LotShortcut]]: ...

    @overload
    def get_sorted_lots(
        self, mode: Literal[3]
    ) -> dict[SubCategoryTypes, dict[int | str, LotShortcut]]: ...

    def get_sorted_lots(
        self, mode: Literal[1, 2, 3]
    ) -> (
        dict[int | str, LotShortcut]
        | dict[_module_state.SubCategory, dict[int | str, LotShortcut]]
        | dict[SubCategoryTypes, dict[int | str, LotShortcut]]
    ):
        if mode == 1:
            return self.__lots_ids
        elif mode == 2:
            return self.__sorted_by_subcategory_lots
        else:
            return self.__sorted_by_subcategory_type_lots

    def update_lot(self, lot: LotShortcut):
        self.__lots_ids[lot.id] = lot
        if lot.subcategory not in self.__sorted_by_subcategory_lots:
            self.__sorted_by_subcategory_lots[lot.subcategory] = {}
        self.__sorted_by_subcategory_lots[lot.subcategory][lot.id] = lot
        self.__sorted_by_subcategory_type_lots[lot.subcategory.type][lot.id] = lot

    def add_lot(self, lot: LotShortcut):
        if lot.id in self.__lots_ids:
            return
        self.update_lot(lot)

    def get_common_lots(self) -> list[LotShortcut]:
        return list(
            self.__sorted_by_subcategory_type_lots[SubCategoryTypes.COMMON].values()
        )

    def get_currency_lots(self) -> list[LotShortcut]:
        return list(
            self.__sorted_by_subcategory_type_lots[SubCategoryTypes.CURRENCY].values()
        )

    def __str__(self):
        return self.username


class Review:
    def __init__(
        self,
        stars: int | None,
        text: str | None,
        reply: str | None,
        anonymous: bool,
        html: str,
        hidden: bool,
        order_id: str | None = None,
        author: str | None = None,
        author_id: int | None = None,
        by_bot: bool = False,
        reply_by_bot: bool = False,
    ):
        self.stars: int | None = stars
        self.text: str | None = text
        self.reply: str | None = reply
        self.anonymous: bool = anonymous
        self.html: str = html
        self.hidden: bool = hidden
        self.order_id: str | None = (
            order_id[1:] if order_id and order_id.startswith("#") else order_id
        )
        self.author: str | None = author
        self.author_id: int | None = author_id
        self.by_bot: bool = by_bot
        self.reply_by_bot: bool = reply_by_bot


class Balance:
    def __init__(
        self,
        total_rub: float,
        available_rub: float,
        total_usd: float,
        available_usd: float,
        total_eur: float,
        available_eur: float,
    ):
        self.total_rub: float = total_rub
        self.available_rub: float = available_rub
        self.total_usd: float = total_usd
        self.available_usd: float = available_usd
        self.total_eur: float = total_eur
        self.available_eur: float = available_eur


class PaymentMethod:
    def __init__(
        self, name: str | None, price: float, currency: Currency, position: int | None
    ):
        self.name: str | None = name
        self.price: float = price
        self.currency: Currency = currency
        self.position: int | None = position
