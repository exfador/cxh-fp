from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from telebot.types import InlineKeyboardMarkup as K
from tg_bot.keyboard_views.styled_button import StyledButton as B
from tg_bot import CBT, MENU_CFG
from tg_bot.utils import NotificationTypes, bool_to_text, add_navigation_buttons
import tg_bot.keyboards as _module_state
from tg_bot.constants.button_styles import BUTTON_PRIMARY
from tg_bot.constants.section_layouts import (
    BLACKLIST_SETTINGS_ROWS,
    NOTIFICATION_SETTINGS_ROWS,
    REVIEW_RATINGS,
    REVIEW_ENABLED,
    REVIEW_DISABLED,
    NOTIFICATION_ENABLED,
    NOTIFICATION_DISABLED,
)
from tg_bot.keyboard_views.section_builder import (
    settings_keyboard,
    section_back,
    translated_button,
)


def authorized_users(c: Cardinal, offset: int):
    kb = K()
    p = f"{CBT.SWITCH}:Telegram"

    def l(s):
        return "🟢" if c.MAIN_CFG["Telegram"].getboolean(s) else "🔴"

    kb.add(
        B(
            _module_state._("tg_block_login", l("blockLogin")),
            None,
            f"{p}:blockLogin:{offset}",
        )
    )
    users = list(c.telegram.authorized_users.keys())[
        offset : offset + MENU_CFG.AUTHORIZED_USERS_BTNS_AMOUNT
    ]
    for user_id in users:
        kb.row(
            B(
                f"{user_id}",
                callback_data=f"{CBT.AUTHORIZED_USER_SETTINGS}:{user_id}:{offset}",
            )
        )
    kb = add_navigation_buttons(
        kb,
        offset,
        MENU_CFG.AUTHORIZED_USERS_BTNS_AMOUNT,
        len(users),
        len(c.telegram.authorized_users),
        CBT.AUTHORIZED_USERS,
    )
    kb.add(B(_module_state._("gl_back"), None, CBT.MAIN2))
    return kb


def authorized_user_settings(c: Cardinal, user_id: int, offset: int, user_link: bool):
    kb = K()
    if user_link:
        kb.add(
            B(_module_state._("menu_open_user_button"), url=f"tg://user?id={user_id}")
        )
    kb.add(B(_module_state._("gl_back"), None, f"{CBT.AUTHORIZED_USERS}:{offset}"))
    return kb


def proxy(c: Cardinal, offset: int, proxies: dict[str, bool]):
    kb = K()
    ps = list(c.proxy_dict.items())[offset : offset + MENU_CFG.PROXY_BTNS_AMOUNT]
    now_proxy = c.MAIN_CFG["Proxy"]["proxy"]
    for i, p in ps:
        work = proxies.get(p)
        e = "🟢" if work else "🟡" if work is None else "🔴"
        if p == now_proxy:
            b1 = B(f"{e}✅ {p}", callback_data=CBT.EMPTY)
        else:
            b1 = B(f"{e} {p}", callback_data=f"{CBT.CHOOSE_PROXY}:{offset}:{i}")
        kb.row(b1, B("🗑️", callback_data=f"{CBT.DELETE_PROXY}:{offset}:{i}"))
    kb = add_navigation_buttons(
        kb,
        offset,
        MENU_CFG.PROXY_BTNS_AMOUNT,
        len(ps),
        len(c.proxy_dict.items()),
        CBT.PROXY,
    )
    kb.row(B(_module_state._("prx_proxy_add"), None, f"{CBT.ADD_PROXY}:{offset}"))
    kb.add(B(_module_state._("gl_back"), None, CBT.MAIN2))
    return kb


def review_reply_row(c, rating, translate):
    field = f"star{rating}Reply"
    enabled = c.MAIN_CFG["ReviewReply"].getboolean(field)
    state = REVIEW_ENABLED if enabled else REVIEW_DISABLED
    return (
        B(
            translate("review_rating_label", rating),
            callback_data=f"{CBT.SEND_REVIEW_REPLY_TEXT}:{rating}",
        ),
        B(
            translate("review_reply_toggle", state),
            callback_data=f"{CBT.SWITCH}:ReviewReply:{field}",
        ),
        B(
            translate("review_reply_edit"),
            callback_data=f"{CBT.EDIT_REVIEW_REPLY_TEXT}:{rating}",
        ),
    )


def review_reply_settings(c: Cardinal) -> K:
    translate = _module_state._
    kb = K()
    for rating in REVIEW_RATINGS:
        kb.row(*review_reply_row(c, rating, translate))
    return section_back(kb, translate, CBT.MAIN2)


def notification_button(c, chat_id, notification_name, label, translate):
    notification = getattr(NotificationTypes, notification_name)
    enabled = c.telegram.is_notification_enabled(chat_id, notification)
    state = NOTIFICATION_ENABLED if enabled else NOTIFICATION_DISABLED
    return B(
        translate(label, state),
        callback_data=f"{CBT.SWITCH_TG_NOTIFICATIONS}:{chat_id}:{notification}",
    )


def notifications_settings(c: Cardinal, chat_id: int) -> K:
    translate = _module_state._
    kb = K()
    for row in NOTIFICATION_SETTINGS_ROWS:
        kb.row(*(notification_button(c, chat_id, *item, translate) for item in row))
    return section_back(kb, translate, CBT.MAIN)


def blacklist_settings(c: Cardinal) -> K:
    from tg_bot.keyboard_views.operator import operator_button

    translate = _module_state._
    kb = settings_keyboard(c.MAIN_CFG, "BlockList", BLACKLIST_SETTINGS_ROWS, translate)
    kb.row(
        operator_button("operator_bl_add", "bl_add"),
        operator_button("operator_bl_remove", "bl_remove"),
    )
    kb.row(operator_button("operator_bl_list", "bl_list"))
    return section_back(kb, translate, CBT.MAIN2)


def commands_list(c: Cardinal, offset: int) -> K:
    kb = K()
    commands = c.RAW_AR_CFG.sections()[offset : offset + MENU_CFG.AR_BTNS_AMOUNT]
    if not commands and offset != 0:
        offset = 0
        commands = c.RAW_AR_CFG.sections()[offset : offset + MENU_CFG.AR_BTNS_AMOUNT]
    for index, cmd in enumerate(commands):
        kb.add(
            B(
                f"{bool_to_text(c.RAW_AR_CFG.get(cmd, 'enabled'))} {cmd}",
                None,
                f"{CBT.EDIT_CMD}:{offset + index}:{offset}",
            )
        )
    kb = add_navigation_buttons(
        kb,
        offset,
        MENU_CFG.AR_BTNS_AMOUNT,
        len(commands),
        len(c.RAW_AR_CFG.sections()),
        CBT.CMD_LIST,
    )
    kb.add(B(_module_state._("ar_to_ar"), None, f"{CBT.CATEGORY}:ar")).add(
        B(_module_state._("ar_to_mm"), None, CBT.MAIN)
    )
    return kb


def command_status_button(command, index, offset, translate):
    state = bool_to_text(
        command.get("enabled"), translate("gl_on"), translate("gl_off")
    )
    return B(state, callback_data=f"{CBT.SWITCH_CMD_SETTING}:{index}:{offset}:enabled")


def command_notification_button(command, index, offset, translate):
    state = bool_to_text(
        command.get("telegramNotification"), NOTIFICATION_ENABLED, NOTIFICATION_DISABLED
    )
    return B(
        translate("ar_notification", state),
        callback_data=f"{CBT.SWITCH_CMD_SETTING}:{index}:{offset}:telegramNotification",
    )


def edit_command(c: Cardinal, command_index: int, offset: int) -> K:
    translate = _module_state._
    command = c.RAW_AR_CFG[c.RAW_AR_CFG.sections()[command_index]]
    suffix = f"{command_index}:{offset}"
    kb = K().row(command_status_button(command, command_index, offset, translate))
    kb.row(
        translated_button(
            translate,
            "ar_edit_response",
            f"{CBT.EDIT_CMD_RESPONSE_TEXT}:{suffix}",
            BUTTON_PRIMARY,
        ),
        translated_button(
            translate,
            "ar_edit_notification",
            f"{CBT.EDIT_CMD_NOTIFICATION_TEXT}:{suffix}",
        ),
    )
    kb.row(command_notification_button(command, command_index, offset, translate))
    kb.row(translated_button(translate, "gl_delete", f"{CBT.DEL_CMD}:{suffix}"))
    kb.row(
        translated_button(translate, "gl_back", f"{CBT.CMD_LIST}:{offset}"),
        translated_button(translate, "gl_refresh", f"{CBT.EDIT_CMD}:{suffix}"),
    )
    return kb
