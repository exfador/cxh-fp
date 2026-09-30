from dataclasses import dataclass

from FunPayAPI import types
from FunPayAPI.accounts.constants import (
    CATALOG_CURRENCY_MISSING,
    CATALOG_INTERNAL_ATTRIBUTES,
    CATALOG_PRICE_MISSING,
    CATALOG_SELLER_LINK_MISSING,
    CATALOG_SELLER_LINK_SELECTOR,
    CATALOG_SELLER_MISSING,
    CATALOG_SELLER_NAME_MISSING,
    CATALOG_TRUE_FLAG,
    OFFER_CATEGORY_MISSING,
)
from FunPayAPI.accounts.offer_forms import editor_price
from FunPayAPI.accounts.public_offers import public_offer_id, public_user_id
from FunPayAPI.common.utils import parse_currency


@dataclass(frozen=True)
class CatalogOffer:
    identifier: str
    server: str | None
    side: str | None
    description: str | None
    amount: int | None
    price: float
    currency: types.Currency
    attributes: dict
    automatic: bool
    promoted: bool


def catalog_text(offer, selector: str):
    element = offer.select_one(selector)
    return element.get_text() if element else None


def catalog_amount(offer):
    text = catalog_text(offer, ".tc-amount")
    value = "".join(text.split()) if text else None
    return int(value) if value and value.isascii() and value.isdecimal() else None


def catalog_attributes(offer):
    return {
        key.removeprefix("data-"): int(value)
        if isinstance(value, str) and value.isascii() and value.isdecimal()
        else value
        for key, value in offer.attrs.items()
        if key.startswith("data-")
    }


def catalog_price(offer, category_type):
    element = offer.select_one(".tc-price")
    if not element:
        raise ValueError(CATALOG_PRICE_MISSING)
    value = element.get("data-s")
    if category_type is types.SubCategoryTypes.CURRENCY:
        text = element.find("div")
        value = text.get_text().rsplit(maxsplit=1)[0] if text else None
    price = editor_price("".join(str(value).split()) if value else None)
    if price is None:
        raise ValueError(CATALOG_PRICE_MISSING)
    return price


def catalog_currency(offer):
    element = offer.select_one(".tc-price .unit")
    if not element:
        raise ValueError(CATALOG_CURRENCY_MISSING)
    return parse_currency(element.get_text())


def catalog_offer(offer, category_type, currency):
    attributes = catalog_attributes(offer)
    return CatalogOffer(
        public_offer_id(offer["href"]),
        catalog_text(offer, ".tc-server"),
        catalog_text(offer, ".tc-side"),
        catalog_text(offer, ".tc-desc-text"),
        catalog_amount(offer),
        catalog_price(offer, category_type),
        currency if currency is not None else catalog_currency(offer),
        attributes,
        attributes.get("auto") == CATALOG_TRUE_FLAG,
        "offer-promo" in offer.get("class", []),
    )


def catalog_seller_identity(element):
    link = element.select_one(CATALOG_SELLER_LINK_SELECTOR)
    if not link:
        raise ValueError(CATALOG_SELLER_LINK_MISSING)
    return public_user_id(link.get("data-href") or link["href"])


def catalog_seller(offer, fields, sellers):
    element = offer.select_one(".tc-user")
    if not element:
        raise ValueError(CATALOG_SELLER_MISSING)
    markup = str(element)
    if markup in sellers:
        return sellers[markup]
    name = catalog_text(element, ".media-user-name")
    if not name:
        raise ValueError(CATALOG_SELLER_NAME_MISSING)
    rating = element.select_one(".rating-stars")
    reviews = catalog_text(element, ".media-user-reviews") or ""
    count = "".join(char for char in reviews if char.isascii() and char.isdecimal())
    seller = types.SellerShortcut(
        catalog_seller_identity(element),
        name.strip(),
        fields.attributes.get("online") == CATALOG_TRUE_FLAG,
        len(rating.select("i.fas")) if rating else None,
        int(count) if count else 0,
        markup,
    )
    sellers[markup] = seller
    return seller


def catalog_shortcut(offer, fields, subcategory, seller):
    attributes = {
        key: value
        for key, value in fields.attributes.items()
        if key not in CATALOG_INTERNAL_ATTRIBUTES
    }
    return types.LotShortcut(
        fields.identifier,
        fields.server,
        fields.side,
        fields.description,
        fields.amount,
        fields.price,
        fields.currency,
        subcategory,
        seller,
        fields.automatic,
        fields.promoted,
        attributes,
        str(offer),
    )


def parse_public_catalog(account, parser, category_type, category_id):
    offers = parser.select("a.tc-item")
    if not offers:
        return []
    subcategory = account.get_subcategory(category_type, category_id)
    if not subcategory:
        raise ValueError(OFFER_CATEGORY_MISSING)
    result, sellers = [], {}
    currency = None
    for offer in offers:
        fields = catalog_offer(offer, category_type, currency)
        currency = fields.currency
        seller = catalog_seller(offer, fields, sellers)
        result.append(catalog_shortcut(offer, fields, subcategory, seller))
    account.currency = currency
    return result
