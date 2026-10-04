from html import escape

from telebot.types import InlineKeyboardButton as B
from telebot.types import InlineKeyboardMarkup as K

from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot.constants.order_reminder import (
    REMINDER_ORDER_VARIABLE,
    REMINDER_REPORT_SECONDS,
    REMINDER_USERNAME_VARIABLE,
)


def translate(key, *args):
    return Localizer().translate(key, *args)


def reminder_text(service, now):
    store = service.store
    state = translate("cr_state_on" if store.enabled else "cr_state_off")
    block = "\n".join(
        (
            translate("cr_panel_state", state),
            translate("cr_panel_hours", store.hours),
            translate("cr_panel_sent", store.sent_since(now - REMINDER_REPORT_SECONDS)),
        )
    )
    lines = [
        translate("cr_panel_title"),
        translate("cr_panel_about", store.hours),
        f"<blockquote>{block}</blockquote>",
    ]
    if service.cardinal.old_mode_enabled:
        lines.append(f"⚠️ {translate('cr_problem_old_mode')}")
    custom = translate("cr_text_custom" if store.text else "cr_text_default")
    lines.append(
        f"{custom}\n<blockquote>{escape(service.template())}</blockquote>\n"
        + translate("cr_variables", REMINDER_USERNAME_VARIABLE, REMINDER_ORDER_VARIABLE)
    )
    return "\n\n".join(lines)


def reminder_keyboard(service):
    store = service.store
    toggle = "cr_toggle_on" if store.enabled else "cr_toggle_off"
    keyboard = K().row(B(translate(toggle), callback_data=CBT.CONFIRM_REMINDER_TOGGLE))
    keyboard.row(
        B(
            translate("cr_hours_button", store.hours),
            callback_data=CBT.CONFIRM_REMINDER_HOURS,
        ),
        B(translate("cr_text_button"), callback_data=CBT.CONFIRM_REMINDER_TEXT),
    )
    if store.text:
        keyboard.row(
            B(translate("cr_reset_button"), callback_data=CBT.CONFIRM_REMINDER_RESET)
        )
    return keyboard
