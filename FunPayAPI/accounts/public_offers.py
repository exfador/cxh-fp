from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

from FunPayAPI import types
from FunPayAPI.accounts.constants import (
    LOT_DESCRIPTION_LABELS,
    LOT_IMAGE_LABELS,
    LOT_NOT_FOUND_TITLES,
    MAX_OFFER_ID_LENGTH,
    MAX_QUERY_FIELDS,
    OFFER_LINK_INVALID,
    OFFER_CATEGORY_LINK_MISSING,
    PUBLIC_OFFER_PATHS,
    USER_PROFILE_LINK_INVALID,
    USER_PROFILE_PATH,
    MAX_USER_ID_LENGTH,
)
from FunPayAPI.security.constants import API_LOCALES
from FunPayAPI.security.urls import normalize_api_url, validate_api_url


def public_offer_id(value: str) -> str:
    parsed = urlsplit(normalize_api_url(value, None))
    if parsed.path.rstrip("/") not in PUBLIC_OFFER_PATHS:
        raise ValueError(OFFER_LINK_INVALID)
    values = parse_qs(parsed.query, max_num_fields=MAX_QUERY_FIELDS).get("id", [])
    if len(values) != 1:
        raise ValueError(OFFER_LINK_INVALID)
    identifier = values[0]
    allowed = identifier.replace("-", "")
    if not allowed.isascii() or not allowed.isalnum():
        raise ValueError(OFFER_LINK_INVALID)
    if len(identifier) > MAX_OFFER_ID_LENGTH:
        raise ValueError(OFFER_LINK_INVALID)
    return identifier


def public_user_id(value: str) -> int:
    parsed = urlsplit(validate_api_url(value))
    parts = parsed.path.strip("/").split("/")
    if parts[0] in API_LOCALES:
        parts = parts[1:]
    if len(parts) != 2 or parts[0] != USER_PROFILE_PATH:
        raise ValueError(USER_PROFILE_LINK_INVALID)
    identifier = parts[1]
    if not identifier.isascii() or not identifier.isdecimal():
        raise ValueError(USER_PROFILE_LINK_INVALID)
    if len(identifier) > MAX_USER_ID_LENGTH or int(identifier) <= 0:
        raise ValueError(USER_PROFILE_LINK_INVALID)
    return int(identifier)


def lot_descriptions(parser: BeautifulSoup) -> tuple[str | None, str | None]:
    descriptions = {}
    for item in parser.select("div.param-item"):
        heading = item.find("h5")
        label = heading.get_text(strip=True) if heading else None
        key = LOT_DESCRIPTION_LABELS.get(label)
        content = item.find("div")
        if key and content:
            descriptions[key] = content.get_text()
    return descriptions.get("short"), descriptions.get("full")


def lot_image_urls(parser: BeautifulSoup) -> list[str]:
    result = []
    for item in parser.select("div.param-item"):
        heading = item.find("h5")
        if not heading or heading.get_text(strip=True) not in LOT_IMAGE_LABELS:
            continue
        result.extend(
            photo["href"] for photo in item.select("a.attachments-thumb[href]")
        )
    return result


def lot_seller(account, parser: BeautifulSoup) -> tuple[int, str]:
    seller = parser.select_one(".chat-header .media-user-name a[href]")
    if not seller:
        return account.id, account.username
    seller_path = urlsplit(validate_api_url(seller["href"])).path
    return int(seller_path.rstrip("/").rsplit("/", 1)[-1]), seller.get_text()


def lot_subcategory(account, link: Tag):
    path = urlsplit(validate_api_url(link["href"])).path
    identifier = int(path.rstrip("/").rsplit("/", 1)[-1])
    return account.get_subcategory(types.SubCategoryTypes.COMMON, identifier)


def parse_lot_page(account, parser: BeautifulSoup, lot_id: int):
    heading = parser.find("h1", class_="page-header")
    if heading and heading.get_text(strip=True) in LOT_NOT_FOUND_TITLES:
        return None
    link = parser.find("a", class_="js-back-link")
    if not link or not link.get("href"):
        raise ValueError(OFFER_CATEGORY_LINK_MISSING)
    seller_id, seller_name = lot_seller(account, parser)
    short, full = lot_descriptions(parser)
    return types.LotPage(
        lot_id,
        lot_subcategory(account, link),
        short,
        full,
        lot_image_urls(parser),
        seller_id,
        seller_name,
    )
