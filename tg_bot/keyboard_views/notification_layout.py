from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot.constants.message_formatting import NOTIFICATION_BUTTON_COLUMNS


def notification_keyboard(buttons):
    keyboard = InlineKeyboardMarkup()
    for offset in range(0, len(buttons), NOTIFICATION_BUTTON_COLUMNS):
        keyboard.row(*buttons[offset : offset + NOTIFICATION_BUTTON_COLUMNS])
    return keyboard


def notification_button(label, callback):
    return InlineKeyboardButton(Localizer().translate(label), callback_data=callback)


def refund_notification_buttons(order_id, username, node_id, confirmation, no_refund):
    if no_refund:
        return []
    payload = f"{order_id}:{node_id}:{username}"
    if confirmation:
        return [
            notification_button("gl_yes", f"{CBT.REFUND_CONFIRMED}:{payload}"),
            notification_button("gl_no", f"{CBT.REFUND_CANCELLED}:{payload}"),
        ]
    return [notification_button("ord_refund", f"{CBT.REQUEST_REFUND}:{payload}")]


def reply_notification_buttons(node_id, username, again, extend):
    buttons = [
        notification_button(
            "msg_reply2" if again else "msg_reply",
            f"{CBT.SEND_FP_MESSAGE}:{node_id}:{username}",
        ),
        notification_button(
            "msg_templates",
            f"{CBT.TMPLT_LIST_ANS_MODE}:0:{node_id}:{username}:{int(again)}:{int(extend)}",
        ),
    ]
    if extend:
        buttons.append(
            notification_button("msg_more", f"{CBT.EXTEND_CHAT}:{node_id}:{username}")
        )
    return buttons
