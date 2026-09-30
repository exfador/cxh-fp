from dataclasses import dataclass
from html import escape
import re
from time import time
import unicodedata

import psutil

from FunPayAPI.common.enums import SubCategoryTypes, OrderStatuses
from locales.localizer import Localizer
from tg_bot.constants.menu import (
    MENU_PAGE_SIZE,
    MENU_SEARCH_MAX_LENGTH,
    MENU_TITLE_MAX_LENGTH,
    MENU_ORDER_ID_PATTERN,
    MENU_ORDER_LIMIT,
)


@dataclass(frozen=True)
class MenuLot:
    id: int
    title: str


@dataclass(frozen=True)
class MenuOrder:
    identifier: str
    title: str


def normalize_search(value):
    text = unicodedata.normalize("NFKC", value).strip()
    if not text or len(text) > MENU_SEARCH_MAX_LENGTH:
        raise ValueError("Invalid menu search")
    return text.casefold()


def compact_title(value):
    text = " ".join(str(value or "").split())
    return (
        text
        if len(text) <= MENU_TITLE_MAX_LENGTH
        else text[:MENU_TITLE_MAX_LENGTH] + "…"
    )


def cached_lots(cardinal, query=""):
    profile = cardinal.profile
    if profile is None:
        return []
    result = []
    for lot in profile.get_lots():
        if lot.subcategory.type is not SubCategoryTypes.COMMON:
            continue
        identifier = str(lot.id)
        if not identifier.isascii() or not identifier.isdecimal():
            continue
        title = str(lot.description or lot.subcategory.name or lot.id)
        if (
            query
            and query not in unicodedata.normalize("NFKC", title).casefold()
            and query != identifier
        ):
            continue
        result.append(MenuLot(int(identifier), compact_title(title)))
    return sorted(result, key=lambda lot: lot.id)


def menu_page(items, argument):
    text = str(argument)
    if text == "-":
        text = "0"
    if not text.isascii() or not text.isdecimal() or len(text) > 6:
        raise ValueError("Invalid menu page")
    last = max(0, (len(items) - 1) // MENU_PAGE_SIZE)
    page = min(int(text), last)
    return items[page * MENU_PAGE_SIZE : (page + 1) * MENU_PAGE_SIZE], page


def cached_orders(cardinal):
    runner = cardinal.runner
    if runner is None:
        return []
    return order_rows(list(runner.saved_orders.values())[:MENU_ORDER_LIMIT])


def order_rows(orders):
    statuses = {
        OrderStatuses.PAID: "menu_paid",
        OrderStatuses.CLOSED: "menu_closed",
        OrderStatuses.REFUNDED: "menu_refunded",
    }
    translate = Localizer().translate
    result = []
    for order in orders[:MENU_ORDER_LIMIT]:
        if not re.fullmatch(MENU_ORDER_ID_PATTERN, str(order.id)):
            continue
        status = translate(statuses.get(order.status, "menu_unknown"))
        title = f"#{order.id} · {order.price:g} {order.currency.name} · {status}"
        result.append(MenuOrder(order.id, title))
    return result


def cached_chats(cardinal):
    if not cardinal.account.is_initiated:
        return []
    return list(cardinal.account.get_chats().values())


def home_text(cardinal):
    translate = Localizer().translate
    status = translate(
        "menu_connected" if cardinal.account.is_initiated else "menu_connecting"
    )
    status += home_profile_summary(cardinal, translate)
    account_name = escape(str(cardinal.account.username or translate("menu_unknown")))
    return translate(
        "menu_home_text",
        cardinal.VERSION,
        account_name,
        status,
        cardinal.account.active_sales or 0,
        len(cached_lots(cardinal)),
        sum(chat.unread for chat in cached_chats(cardinal)),
    )


def home_profile_summary(cardinal, translate):
    if not cardinal.account.is_initiated:
        return ""
    identifier = escape(str(cardinal.account.id or translate("menu_unknown")))
    text = translate("menu_home_profile_id", identifier)
    if cardinal.balance is not None:
        text += translate(
            "menu_home_profile_balance",
            cardinal.balance.total_rub,
            cardinal.balance.available_rub,
        )
    return text


def account_text(cardinal):
    translate = Localizer().translate
    account = cardinal.account
    text = translate(
        "menu_account_text",
        escape(str(account.username or translate("menu_unknown"))),
        account.id or "—",
        account.active_sales or 0,
    )
    if cardinal.balance is not None:
        balance = cardinal.balance
        text += translate(
            "menu_balance_text",
            balance.total_rub,
            balance.available_rub,
            balance.total_usd,
            balance.available_usd,
            balance.total_eur,
            balance.available_eur,
        )
    return text + translate("menu_cache_note")


def health_text(cardinal):
    translate = Localizer().translate
    process = psutil.Process()
    enabled = sum(plugin.enabled for plugin in cardinal.plugins.values())
    return translate(
        "menu_health_text",
        cardinal.VERSION,
        max(0, int(time() - cardinal.start_time)),
        process.memory_info().rss // 1048576,
        enabled,
        len(cardinal.plugins),
        len(cached_lots(cardinal)),
        len(cached_orders(cardinal)),
    )
