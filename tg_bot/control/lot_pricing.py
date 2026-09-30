import logging

from FunPayAPI.accounts.price_quotes import validate_identifier, validate_price
from locales.localizer import Localizer
from tg_bot.constants.lot_pricing import (
    PRIVATE_CHAT_TYPE,
    COMMAND_ARGUMENT_COUNTS,
    COMMAND_WITH_PRICE_COUNT,
    INVALID_COMMAND,
    PRICING_LOGGER,
    PRICING_FAILURE_LOG,
)


class LotPricing:
    def send_lot_price_quote(self, message):
        if not message.from_user or message.from_user.id not in self.authorized_users:
            return
        translate = Localizer().translate
        if message.chat.type != PRIVATE_CHAT_TYPE:
            self.bot.send_message(message.chat.id, translate("lot_price_private"))
            return
        try:
            lot_id, price = self.parse_lot_price_command(message.text)
        except ValueError:
            self.bot.send_message(message.chat.id, translate("lot_price_usage"))
            return
        self.calculate_lot_price_quote(message.chat.id, lot_id, price)

    def calculate_lot_price_quote(self, chat_id, lot_id, price):
        translate = Localizer().translate
        try:
            quote = self.cardinal.account.get_lot_price_quote(lot_id, price)
        except Exception as error:
            logging.getLogger(PRICING_LOGGER).warning(
                PRICING_FAILURE_LOG,
                lot_id,
                type(error).__name__,
            )
            self.bot.send_message(chat_id, translate("lot_price_error"))
            return
        self.bot.send_message(
            chat_id,
            translate(
                "lot_price_result",
                quote.lot_id,
                quote.seller_price,
                quote.buyer_sbp_price,
                quote.difference,
            ),
        )

    def parse_lot_price_command(self, text):
        arguments = (text or "").split()
        if len(arguments) not in COMMAND_ARGUMENT_COUNTS:
            raise ValueError(INVALID_COMMAND)
        lot_id = validate_identifier(arguments[1])
        price = (
            validate_price(arguments[2])
            if len(arguments) == COMMAND_WITH_PRICE_COUNT
            else None
        )
        return lot_id, price
