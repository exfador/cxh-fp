from html import escape

from FunPayAPI.common.enums import OrderStatuses
from tg_bot.constants.menu import MENU_ORDER_DATE_FORMAT, MENU_ORDER_TEXT_LIMIT
from tg_bot.sales_stats import amount_text

ORDER_STATUS_KEYS = {
    OrderStatuses.PAID: "order_status_paid",
    OrderStatuses.CLOSED: "order_status_closed",
    OrderStatuses.REFUNDED: "order_status_refunded",
}


def clip(value):
    text = " ".join(str(value or "").split())
    if len(text) <= MENU_ORDER_TEXT_LIMIT:
        return text
    return text[:MENU_ORDER_TEXT_LIMIT] + "…"


def review_text(order, translate):
    review = getattr(order, "review", None)
    stars = getattr(review, "stars", None)
    if not stars:
        return ""
    text = clip(getattr(review, "text", "") or "")
    quote = f"\n<i>{escape(text)}</i>" if text else ""
    return translate("order_card_review", "⭐" * int(stars)) + quote


def order_text(shortcut, order, translate):
    status = order.status if order else shortcut.status
    price = order.sum if order else shortcut.price
    currency = order.currency if order else shortcut.currency
    buyer = (order.buyer_username if order else None) or shortcut.buyer_username
    description = (order.short_description if order else None) or shortcut.description
    amount = order.amount if order else getattr(shortcut, "amount", None)
    money = f"{amount_text(float(price), translate('menu_stats_decimal'))} {currency}"
    block = translate(
        "order_card_block",
        translate(ORDER_STATUS_KEYS.get(status, "menu_unknown")),
        escape(str(buyer or "—")),
        money,
        shortcut.date.strftime(MENU_ORDER_DATE_FORMAT),
    )
    parts = [
        translate("order_card_title", escape(str(shortcut.id))),
        f"<blockquote>{block}</blockquote>",
        translate(
            "order_card_item",
            escape(clip(shortcut.subcategory_name or "—")),
            escape(clip(description or "—")),
        ),
    ]
    if amount and amount > 1:
        parts[-1] += "\n" + translate("order_card_amount", amount)
    review = review_text(order, translate)
    if review:
        parts.append(review)
    if order is None:
        parts.append(translate("order_card_offline"))
    return "\n\n".join(parts)
