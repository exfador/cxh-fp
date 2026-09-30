from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from telebot.types import InlineKeyboardMarkup as K, InlineKeyboardButton as B
from tg_bot import CBT
import tg_bot.keyboards as _module_state
from app.constants.languages import LANGUAGE_LABELS
from tg_bot.constants.button_styles import BUTTON_PRIMARY
from tg_bot.constants.section_layouts import (
    MAIN_SETTINGS_ROWS,
    MESSAGE_SETTINGS_ROWS,
    GREETING_SETTINGS_ROWS,
    ORDER_SETTINGS_ROWS,
    SETTINGS_HELP_LABEL,
)
from tg_bot.keyboard_views.section_builder import (
    setting_button,
    settings_keyboard,
    translated_button,
    section_back,
)


def power_off(instance_id: int, state: int) -> K:
    return K().row(
        B(
            _module_state._("menu_shutdown_confirm"),
            callback_data=f"{CBT.SHUT_DOWN}:6:{instance_id}",
        ),
        B(_module_state._("gl_cancel"), callback_data=CBT.CANCEL_SHUTTING_DOWN),
    )


def language_settings(c: Cardinal) -> K:
    lang = c.MAIN_CFG["Other"]["language"]
    langs = LANGUAGE_LABELS
    kb = K()
    lang_buttons = []
    for i in langs:
        cb = f"{CBT.LANG}:{i}" if lang != i else CBT.EMPTY
        text = langs[i] if lang != i else f"✓ {langs[i]}"
        lang_buttons.append(B(text, callback_data=cb))
    kb.row(*lang_buttons)
    kb.add(B(_module_state._("gl_back"), None, CBT.MAIN))
    return kb


def main_settings(c: Cardinal) -> K:
    translate = _module_state._
    kb = settings_keyboard(c.MAIN_CFG, "FunPay", MAIN_SETTINGS_ROWS, translate)
    kb.row(
        setting_button(
            c.MAIN_CFG, "FunPay", "oldMsgGetMode", "gs_old_msg_mode", translate
        ),
        B(SETTINGS_HELP_LABEL, callback_data=CBT.OLD_MOD_HELP),
    )
    if c.old_mode_enabled:
        kb.row(
            setting_button(
                c.MAIN_CFG,
                "FunPay",
                "keepSentMessagesUnread",
                "gs_keep_sent_messages_unread",
                translate,
            )
        )
    return section_back(kb, translate, CBT.MAIN)


def new_message_view_settings(c: Cardinal) -> K:
    translate = _module_state._
    kb = settings_keyboard(
        c.MAIN_CFG, "NewMessageView", MESSAGE_SETTINGS_ROWS, translate
    )
    return section_back(kb, translate, CBT.MAIN2)


def greeting_settings(c: Cardinal) -> K:
    translate = _module_state._
    config = c.MAIN_CFG["Greetings"]
    kb = settings_keyboard(c.MAIN_CFG, "Greetings", GREETING_SETTINGS_ROWS, translate)
    actions = [
        translated_button(
            translate, "gr_edit_message", CBT.EDIT_GREETINGS_TEXT, BUTTON_PRIMARY
        )
    ]
    if not config.getboolean("onlyNewChats"):
        cooldown = float(config["greetingsCooldown"])
        cooldown = int(cooldown) if int(cooldown) == cooldown else cooldown
        actions.append(
            B(
                translate("gr_edit_cooldown", cooldown),
                callback_data=CBT.EDIT_GREETINGS_COOLDOWN,
            )
        )
    kb.row(*actions)
    return section_back(kb, translate, CBT.MAIN2)


def order_confirm_reply_settings(c: Cardinal) -> K:
    translate = _module_state._
    kb = settings_keyboard(c.MAIN_CFG, "OrderConfirm", ORDER_SETTINGS_ROWS, translate)
    kb.row(
        translated_button(
            translate,
            "oc_edit_message",
            CBT.EDIT_ORDER_CONFIRM_REPLY_TEXT,
            BUTTON_PRIMARY,
        )
    )
    return section_back(kb, translate, CBT.MAIN2)
