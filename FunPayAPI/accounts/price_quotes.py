from decimal import Decimal
import re
import unicodedata

from bs4 import BeautifulSoup

from FunPayAPI.accounts.constants.pricing import (
    CATEGORY_FIELD_SELECTOR,
    INVALID_IDENTIFIER,
    INVALID_PRICE,
    MAX_IDENTIFIER_LENGTH,
    MAX_PRICE_LENGTH,
    MONEY_QUANTUM,
    PRICE_FIELD_SELECTOR,
    PRICE_PATTERN,
    PRICE_UNIT_SELECTOR,
    RUBLE_PRICE_REQUIRED,
    SBP_METHOD_REQUIRED,
    SBP_PREFIXES,
)
from FunPayAPI.accounts.offer_forms import offer_editor_form
from FunPayAPI.common.enums import Currency, SubCategoryTypes
from FunPayAPI.common.utils import parse_currency
from FunPayAPI.models.price_quote import LotPriceQuote
from FunPayAPI.security.urls import build_api_query


def validate_price(value) -> Decimal:
    text = str(value).strip()
    if len(text) > MAX_PRICE_LENGTH or not re.fullmatch(PRICE_PATTERN, text):
        raise ValueError(INVALID_PRICE)
    price = Decimal(text.replace(",", "."))
    if price <= 0:
        raise ValueError(INVALID_PRICE)
    return price.quantize(MONEY_QUANTUM)


def validate_identifier(value) -> int:
    text = str(value)
    if not text.isascii() or not text.isdecimal():
        raise ValueError(INVALID_IDENTIFIER)
    if len(text) > MAX_IDENTIFIER_LENGTH or int(text) <= 0:
        raise ValueError(INVALID_IDENTIFIER)
    return int(text)


def editor_price_context(account, lot_id):
    response = account.method(
        "get",
        build_api_query("lots/offerEdit", {"offer": lot_id}),
        {},
        {},
        raise_not_200=True,
    )
    parser = BeautifulSoup(response.content.decode(), "lxml")
    form = offer_editor_form(parser, response, lot_id)
    category = form.select_one(CATEGORY_FIELD_SELECTOR)
    price = form.select_one(PRICE_FIELD_SELECTOR)
    unit = form.select_one(PRICE_UNIT_SELECTOR)
    if not category or not price or not unit:
        raise ValueError(RUBLE_PRICE_REQUIRED)
    if parse_currency(unit.get_text()) is not Currency.RUB:
        raise ValueError(RUBLE_PRICE_REQUIRED)
    return validate_identifier(category.get("value")), price.get("value")


def select_sbp_method(methods):
    matches = [
        method
        for method in methods
        if method.currency is Currency.RUB
        and unicodedata.normalize("NFKC", method.name)
        .strip()
        .casefold()
        .startswith(SBP_PREFIXES)
    ]
    if len(matches) != 1:
        raise ValueError(SBP_METHOD_REQUIRED)
    return matches[0]


def get_lot_price_quote(account, lot_id, price=None) -> LotPriceQuote:
    identifier = validate_identifier(lot_id)
    override = validate_price(price) if price is not None else None
    category_id, current_price = editor_price_context(account, identifier)
    seller_price = override if override is not None else validate_price(current_price)
    calculation = account.calc(
        SubCategoryTypes.COMMON, subcategory_id=category_id, price=str(seller_price)
    )
    method = select_sbp_method(calculation.methods)
    return LotPriceQuote(
        identifier,
        category_id,
        seller_price,
        validate_price(method.price),
        method.name,
        Currency.RUB,
    )
