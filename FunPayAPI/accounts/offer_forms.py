import html
import json
import math

from bs4 import BeautifulSoup

from FunPayAPI import types
from FunPayAPI.accounts.constants import (
    CHIP_EXCLUDED_FIELDS,
    CURRENCY_FORM_MISSING,
    OFFER_CATEGORY_MISSING,
    OFFER_EMPTY_METADATA,
    OFFER_FORM_MISSING,
    OFFER_FORM_SELECTOR,
    OFFER_METADATA_INVALID,
    OFFER_PRICE_INVALID,
)
from FunPayAPI.accounts.form_fields import parse_form_fields
from FunPayAPI.common import exceptions
from FunPayAPI.common.utils import parse_currency


def offer_editor_form(parser: BeautifulSoup, response, lot_id):
    form = parser.select_one(OFFER_FORM_SELECTOR)
    if form:
        return form
    error = parser.find("p", class_="lead")
    message = error.get_text() if error else OFFER_FORM_MISSING
    raise exceptions.LotParsingError(response, message, lot_id)


def editor_price(value: str | None) -> float | None:
    if not value:
        return None
    price = float(value)
    if not math.isfinite(price) or price < 0:
        raise ValueError(OFFER_PRICE_INVALID)
    return price


def offer_payment_methods(form) -> list[types.PaymentMethod]:
    result = []
    table = form.find("table", class_="table-buyers-prices")
    if not table:
        return result
    for row in table.find_all("tr"):
        heading, cell = row.find("th"), row.find("td")
        if not heading or not cell:
            continue
        price, unit = cell.get_text().rsplit(maxsplit=1)
        result.append(
            types.PaymentMethod(
                heading.get_text(),
                editor_price(price.replace(" ", "").replace("\xa0", "")),
                parse_currency(unit),
                len(result),
            )
        )
    return result


def offer_calculation(form, fields, subcategory, currency):
    price = editor_price(fields.get("price"))
    if price is None:
        return None
    return types.CalcResult(
        types.SubCategoryTypes.COMMON,
        subcategory.id,
        offer_payment_methods(form),
        price,
        None,
        types.Currency.UNKNOWN,
        currency,
    )


def offer_metadata(form) -> dict:
    metadata = json.loads(html.unescape(form.get("data-offer") or OFFER_EMPTY_METADATA))
    if not isinstance(metadata, dict):
        raise ValueError(OFFER_METADATA_INVALID)
    return metadata


def parse_lot_fields(account, response, lot_id):
    parser = BeautifulSoup(response.content.decode(), "lxml")
    form = offer_editor_form(parser, response, lot_id)
    fields = parse_form_fields(form, preserve_unchecked=True)
    subcategory = account.get_subcategory(
        types.SubCategoryTypes.COMMON, int(fields.get("node_id", 0))
    )
    if not subcategory:
        raise exceptions.LotParsingError(response, OFFER_CATEGORY_MISSING, lot_id)
    unit = form.find("span", class_="form-control-feedback")
    currency = parse_currency(unit.get_text()) if unit else account.currency
    calculation = offer_calculation(form, fields, subcategory, currency)
    metadata = offer_metadata(form)
    result = types.LotFields(
        lot_id, fields, subcategory, currency, calculation, metadata.get("amount")
    )
    account.csrf_token = fields.get("csrf_token") or account.csrf_token
    account.currency = currency
    return result


def parse_chip_fields(account, response, subcategory_id):
    parser = BeautifulSoup(response.content.decode(), "lxml")
    game = parser.find("input", attrs={"name": "game"})
    form = game.find_parent("form") if game else None
    if not form:
        raise exceptions.LotParsingError(
            response, CURRENCY_FORM_MISSING, subcategory_id
        )
    fields = parse_form_fields(form, exclude_names=CHIP_EXCLUDED_FIELDS)
    result = types.ChipFields(account.id, subcategory_id, fields)
    account.csrf_token = fields.get("csrf_token") or account.csrf_token
    return result
