from html import escape

from telebot.types import InlineKeyboardButton as B
from telebot.types import InlineKeyboardMarkup as K

from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot.constants.review_reminder import (
    REVIEW_REMINDER_ORDER_VARIABLE,
    REVIEW_REMINDER_REPORT_SECONDS,
    REVIEW_REMINDER_USERNAME_VARIABLE,
)


def translate(key, *args):
    return Localizer().translate(key, *args)


def review_reminder_text(service, now):
    store = service.store
    state = translate("cr_state_on" if store.enabled else "cr_state_off")
    block = "\n".join(
        (
            translate("cr_panel_state", state),
            translate("rv_panel_hours", store.hours),
            translate("rv_panel_waiting", store.waiting()),
            translate(
                "cr_panel_sent", store.sent_since(now - REVIEW_REMINDER_REPORT_SECONDS)
            ),
        )
    )
    custom = translate("cr_text_custom" if store.text else "cr_text_default")
    lines = [
        translate("rv_panel_title"),
        translate("rv_panel_about", store.hours),
        f"<blockquote>{block}</blockquote>",
        f"{custom}\n<blockquote>{escape(service.template())}</blockquote>\n"
        + translate(
            "cr_variables",
            REVIEW_REMINDER_USERNAME_VARIABLE,
            REVIEW_REMINDER_ORDER_VARIABLE,
        ),
    ]
    return "\n\n".join(lines)


def review_reminder_keyboard(service):
    store = service.store
    toggle = "cr_toggle_on" if store.enabled else "cr_toggle_off"
    keyboard = K().row(B(translate(toggle), callback_data=CBT.REVIEW_REMINDER_TOGGLE))
    keyboard.row(
        B(
            translate("cr_hours_button", store.hours),
            callback_data=CBT.REVIEW_REMINDER_HOURS,
        ),
        B(translate("cr_text_button"), callback_data=CBT.REVIEW_REMINDER_TEXT),
    )
    if store.text:
        keyboard.row(
            B(translate("cr_reset_button"), callback_data=CBT.REVIEW_REMINDER_RESET)
        )
    return keyboard
