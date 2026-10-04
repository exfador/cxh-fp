from html import escape

from locales.localizer import Localizer
from FunPayAPI.accounts.price_quotes import validate_identifier
from tg_bot.constants.menu import MENU_PAGE_SIZE
from tg_bot.menu_data import (
    cached_lots,
    cached_orders,
    cached_chats,
    menu_page,
    order_rows,
    updated_at,
)
from tg_bot.keyboard_views.menu import (
    lots_keyboard,
    lot_keyboard,
    orders_keyboard,
    chat_keyboard,
)


class MenuTrading:
    def menu_session(self, call, token):
        return self.menu_store.get(
            token, call.from_user.id, call.message.chat.id, call.message.id
        )

    def menu_lots(self, call, token, argument, refreshed=False):
        session = self.menu_session(call, token)
        lots = cached_lots(self.cardinal, session.query)
        visible, page = menu_page(lots, argument)
        text = Localizer().translate(
            "menu_lots_text",
            len(lots),
            page + 1,
            max(1, (len(lots) + MENU_PAGE_SIZE - 1) // MENU_PAGE_SIZE),
            escape(session.query) or Localizer().translate("menu_all_lots_button"),
        )
        if not lots:
            text = Localizer().translate("menu_lots_empty")
        if refreshed:
            text += updated_at()
        keyboard = lots_keyboard(token, visible, page, len(lots), bool(session.query))
        self.menu_render(call, text, keyboard)

    def menu_reset_lots(self, call, token, argument):
        self.menu_store.update(token, query="")
        self.menu_lots(call, token, 0)

    def menu_refresh_lots(self, call, token, argument):
        if not self.menu_store.begin_read(token, "refresh_lots"):
            return
        try:
            profile = self.cardinal.account.get_user(self.cardinal.account.id)
            if profile.id != self.cardinal.account.id:
                raise ValueError("Unexpected profile owner")
            self.cardinal.profile = profile
            self.menu_lots(call, token, 0, refreshed=True)
        finally:
            self.menu_store.finish_read(token)

    def menu_lot(self, call, token, argument):
        identifier = validate_identifier(argument)
        if not any(lot.id == identifier for lot in cached_lots(self.cardinal)):
            raise ValueError("Offer is not in the owned profile")
        self.menu_store.update(token, lot_id=identifier)
        self.menu_quote(call, token, identifier)

    def menu_quote(self, call, token, identifier, price=None):
        if not self.menu_store.begin_read(token, "quote"):
            self.bot.send_message(
                call.message.chat.id, Localizer().translate("menu_busy")
            )
            return False
        try:
            quote = self.cardinal.account.get_lot_price_quote(identifier, price)
            text = Localizer().translate(
                "lot_price_result",
                quote.lot_id,
                quote.seller_price,
                quote.buyer_sbp_price,
                quote.difference,
            )
            self.menu_render(call, text + updated_at(), lot_keyboard(token, identifier))
            return True
        finally:
            self.menu_store.finish_read(token)

    def menu_orders(self, call, token, argument, refreshed=False):
        session = self.menu_session(call, token)
        orders = (
            list(session.orders)
            if session.orders is not None
            else cached_orders(self.cardinal)
        )
        visible, page = menu_page(orders, argument)
        text = Localizer().translate("menu_orders_text", len(orders), page + 1)
        if not orders:
            text = Localizer().translate("menu_orders_empty")
        if refreshed:
            text += updated_at()
        self.menu_render(call, text, orders_keyboard(token, visible, page, len(orders)))

    def menu_refresh_orders(self, call, token, argument):
        if not self.menu_store.begin_read(token, "refresh_orders"):
            return
        try:
            _, orders, _, _ = self.cardinal.account.get_sales()
            self.menu_store.update(token, orders=tuple(order_rows(orders)))
            self.menu_orders(call, token, 0, refreshed=True)
        finally:
            self.menu_store.finish_read(token)

    def menu_chats(self, call, token, argument):
        chats = cached_chats(self.cardinal)
        unread = [chat for chat in chats if chat.unread]
        text = Localizer().translate("menu_chats_text", len(chats), len(unread))
        self.menu_render(call, text, chat_keyboard(token))
