import logging
import re
import time

from locales.localizer import Localizer
from tg_bot.constants.menu import (
    MENU_LOGGER,
    MENU_ORDER_CACHE_SECONDS,
    MENU_ORDER_ID_PATTERN,
    MENU_ORDER_LIMIT,
)
from tg_bot.keyboard_views.menu import order_keyboard
from tg_bot.menu_data import cached_orders
from tg_bot.order_view import order_text


class MenuOrderDetails:
    def menu_order(self, call, token, argument):
        identifier = str(argument)
        if not re.fullmatch(MENU_ORDER_ID_PATTERN, identifier):
            raise ValueError("Invalid order identifier")
        session = self.menu_session(call, token)
        rows = (
            list(session.orders)
            if session.orders is not None
            else cached_orders(self.cardinal)
        )
        shortcut = next(
            (row.shortcut for row in rows if row.identifier == identifier),
            None,
        )
        if shortcut is None:
            raise ValueError("Order is not in the menu list")
        order = self.order_details(identifier)
        text = order_text(shortcut, order, Localizer().translate)
        from tg_bot.core_operations import delivery_text, text as label
        from tg_bot.control.core_operations import button
        from cardinal_core.order_journal import journal

        text += delivery_text(self.cardinal, identifier)
        keyboard = order_keyboard(token, identifier)
        keyboard.row(
            button(
                token,
                "order_explain",
                label("🔎 Разобраться с заказом", "🔎 Investigate order"),
                identifier,
            )
        )
        if journal(self.cardinal).read(identifier).get("native"):
            keyboard.row(
                button(
                    token,
                    "native_order",
                    label("📦 Выдача и резерв", "📦 Delivery and reservation"),
                    identifier,
                )
            )
        self.menu_render(call, text, keyboard)

    def order_details(self, identifier):
        cache = self.__dict__.setdefault("order_details_cache", {})
        now = time.monotonic()
        cached = cache.get(identifier)
        if cached and now - cached[0] < MENU_ORDER_CACHE_SECONDS:
            return cached[1]
        try:
            order = self.cardinal.account.get_order(identifier)
        except Exception:
            logging.getLogger(MENU_LOGGER).debug("TRACEBACK", exc_info=True)
            return None
        if len(cache) >= MENU_ORDER_LIMIT:
            cache.clear()
        cache[identifier] = (now, order)
        return order
