from __future__ import annotations
from FunPayAPI.common.enums import SubCategoryTypes, Currency
import FunPayAPI.types as _module_state


class CalcResult:
    def __init__(
        self,
        subcategory_type: SubCategoryTypes,
        subcategory_id: int,
        methods: list[_module_state.PaymentMethod],
        price: float,
        min_price_with_commission: float | None,
        min_price_currency: Currency,
        account_currency: Currency,
    ):
        self.subcategory_type: SubCategoryTypes = subcategory_type
        self.subcategory_id: int = subcategory_id
        self.methods: list[_module_state.PaymentMethod] = methods
        self.price: float = price
        self.min_price_with_commission: float | None = min_price_with_commission
        self.min_price_currency: Currency = min_price_currency
        self.account_currency = account_currency

    def get_coefficient(self, currency: Currency):
        if (
            self.min_price_with_commission
            and currency == self.min_price_currency == self.account_currency
        ):
            return self.min_price_with_commission / self.price
        else:
            res = min(
                filter(lambda x: x.currency == currency, self.methods),
                key=lambda x: x.price,
                default=None,
            )
            if not res:
                raise Exception("Невозможно определить коэффициент комиссии.")
            return res.price / self.price

    @property
    def commission_coefficient(self) -> float:
        return self.get_coefficient(self.account_currency)

    @property
    def commission_percent(self) -> float:
        return (self.commission_coefficient - 1) * 100


class Wallet:
    def __init__(
        self,
        type_id: str,
        data: str,
        data_n: int | None = None,
        detail_id: int | None = None,
        is_masked: bool = False,
        type_text: str | None = None,
    ):
        self.detail_id: int | None = detail_id
        self.type_id: str = type_id
        self.data: str = data
        self.is_masked: bool = is_masked
        self.type_text: str = type_text
        self.data_n: int | None = data_n
