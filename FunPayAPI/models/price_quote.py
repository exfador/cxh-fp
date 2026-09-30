from dataclasses import dataclass
from decimal import Decimal

from FunPayAPI.common.enums import Currency


@dataclass(frozen=True)
class LotPriceQuote:
    lot_id: int
    subcategory_id: int
    seller_price: Decimal
    buyer_sbp_price: Decimal
    payment_method: str
    currency: Currency

    @property
    def difference(self) -> Decimal:
        return self.buyer_sbp_price - self.seller_price
