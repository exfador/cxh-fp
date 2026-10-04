import logging
from types import SimpleNamespace

from locales.localizer import Localizer
from FunPayAPI.accounts.price_quotes import validate_price, validate_identifier
from tg_bot.constants.menu import MENU_INPUT_STATE, MENU_FAILURE_LOG, MENU_LOGGER
from tg_bot.menu_data import normalize_search, cached_lots
from tg_bot.keyboard_views.menu import menu_back
from telebot.types import InlineKeyboardMarkup


class MenuInput:
    def menu_search(self, call, token, argument):
        self.menu_prompt(call, token, "search", "menu_search_prompt")

    def menu_price(self, call, token, argument):
        identifier = validate_identifier(argument)
        if not any(lot.id == identifier for lot in cached_lots(self.cardinal)):
            raise ValueError("Offer is not in the owned profile")
        self.menu_store.update(token, lot_id=identifier)
        self.menu_prompt(call, token, "price", "menu_price_prompt", identifier)

    def menu_prompt(self, call, token, action, text_key, lot_id=None):
        self.menu_render(
            call,
            Localizer().translate(text_key),
            menu_back(InlineKeyboardMarkup(), token, "lots"),
        )
        self.set_state(
            call.message.chat.id,
            call.message.id,
            call.from_user.id,
            MENU_INPUT_STATE,
            {"token": token, "action": action, "lot_id": lot_id},
        )

    def menu_input_message(self, message):
        if not self.menu_user_allowed(message.from_user, message.chat):
            return
        state = self.get_state(message.chat.id, message.from_user.id)
        if state is None or state["state"] != MENU_INPUT_STATE:
            return
        token, action = state["data"]["token"], state["data"]["action"]
        session = self.menu_store.get(
            token, message.from_user.id, message.chat.id, state["mid"]
        )
        if session is None:
            token = self.menu_store.create(
                message.from_user.id, message.chat.id, state["mid"]
            )
            session = self.menu_store.update(
                token, lot_id=state["data"].get("lot_id")
            )
        call = SimpleNamespace(
            from_user=message.from_user,
            message=SimpleNamespace(chat=message.chat, id=session.message_id),
            menu_token=token,
            menu_revision=session.revision,
        )
        self.menu_process_input(message, call, token, action, session)

    def menu_process_input(self, message, call, token, action, session):
        try:
            value = self.menu_validate_input(action, message.text)
        except ValueError:
            self.bot.send_message(
                message.chat.id, Localizer().translate(f"menu_{action}_invalid")
            )
            return
        try:
            completed = self.menu_apply_input(call, token, action, session, value)
            if completed and self.menu_response_is_current(call):
                self.clear_state(message.chat.id, message.from_user.id)
        except Exception as error:
            logging.getLogger(MENU_LOGGER).warning(
                MENU_FAILURE_LOG, action, type(error).__name__
            )
            self.bot.send_message(
                message.chat.id, Localizer().translate("menu_action_error")
            )

    def menu_validate_input(self, action, text):
        if action == "search":
            return normalize_search(text or "")
        if action == "price":
            return validate_price(text)
        raise ValueError("Unsupported menu input")

    def menu_apply_input(self, call, token, action, session, value):
        if action == "search":
            self.menu_store.update(token, query=value)
            self.menu_lots(call, token, 0)
            return True
        if action == "price" and session.lot_id is not None:
            return self.menu_quote(call, token, session.lot_id, value)
        raise ValueError("Unsupported menu input")
