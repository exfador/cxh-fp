from __future__ import annotations

import os
from typing import TYPE_CHECKING

from telebot.types import InlineKeyboardButton as B
from telebot.types import InlineKeyboardMarkup as K

import tg_bot.keyboards as _module_state
import Utils
from tg_bot import CBT, MENU_CFG
from tg_bot.constants.message_sections import (
    BUTTON_LABEL_LIMIT,
    CONFIRM_DELETE_PRODUCTS_CALLBACK,
    DELETE_PRODUCTS_CALLBACK,
    DISABLED_SETTING_ICON,
    DOWNLOAD_PRODUCTS_CALLBACK,
    ENABLED_SETTING_ICON,
    INACTIVE_SETTING_ICON,
    LABEL_ELLIPSIS,
    LOT_ICON,
    LOT_SETTINGS,
    PINNED_PLUGIN_ICON,
    PLUGIN_ICON,
    PRODUCT_FILE_ICON,
    PRODUCTS_DIRECTORY,
    PRODUCTS_FALLBACK_PAGE_SIZE,
    SWITCH_LOT_CALLBACK,
    TEMPLATE_ICON,
    TEST_DELIVERY_CALLBACK,
    UPDATE_FUNPAY_LOTS_CALLBACK,
)
from tg_bot.keyboard_views.notification_layout import (
    notification_keyboard,
    refund_notification_buttons,
    reply_notification_buttons,
)
from tg_bot.utils import add_navigation_buttons, bool_to_text
from tg_bot.promotion import plugin_store_keyboard

if TYPE_CHECKING:
    from cardinal import Cardinal


def compact_button_label(value: str, prefix: str = "", suffix: str = "") -> str:
    title = " ".join(value.split())
    available = BUTTON_LABEL_LIMIT - len(prefix) - len(suffix)
    if len(title) > available:
        title = title[: available - len(LABEL_ELLIPSIS)].rstrip() + LABEL_ELLIPSIS
    return f"{prefix}{title}{suffix}"


def translated_button(key: str, callback: str) -> B:
    return B(_module_state._(key), callback_data=callback)


def delivery_list_footer(keyboard: K) -> K:
    return keyboard.row(
        translated_button("ad_to_ad", f"{CBT.CATEGORY}:ad"),
        translated_button("ad_to_mm", CBT.MAIN),
    )


def products_files_list(offset: int) -> K:
    keyboard = K()
    files = os.listdir(PRODUCTS_DIRECTORY)[offset : offset + MENU_CFG.PF_BTNS_AMOUNT]
    if not files and offset != 0:
        offset = 0
        files = os.listdir(PRODUCTS_DIRECTORY)[
            offset : offset + PRODUCTS_FALLBACK_PAGE_SIZE
        ]
    for index, name in enumerate(files):
        amount = Utils.cardinal_tools.count_products(f"{PRODUCTS_DIRECTORY}/{name}")
        label = compact_button_label(
            name, f"{PRODUCT_FILE_ICON} ", f" · {amount} {_module_state._('gl_pcs')}"
        )
        keyboard.add(
            B(
                label,
                callback_data=f"{CBT.EDIT_PRODUCTS_FILE}:{offset + index}:{offset}",
            )
        )
    keyboard = add_navigation_buttons(
        keyboard,
        offset,
        MENU_CFG.PF_BTNS_AMOUNT,
        len(files),
        len(os.listdir(PRODUCTS_DIRECTORY)),
        CBT.PRODUCTS_FILES_LIST,
    )
    return delivery_list_footer(keyboard)


def products_delete_buttons(
    keyboard: K, file_number: int, offset: int, confirmation: bool
) -> K:
    if not confirmation:
        return keyboard.add(
            translated_button(
                "gl_delete", f"{DELETE_PRODUCTS_CALLBACK}:{file_number}:{offset}"
            )
        )
    return keyboard.row(
        translated_button(
            "gl_yes", f"{CONFIRM_DELETE_PRODUCTS_CALLBACK}:{file_number}:{offset}"
        ),
        translated_button("gl_no", f"{CBT.EDIT_PRODUCTS_FILE}:{file_number}:{offset}"),
    )


def products_file_edit(file_number: int, offset: int, confirmation: bool = False) -> K:
    keyboard = K().row(
        translated_button(
            "gf_add_goods",
            f"{CBT.ADD_PRODUCTS_TO_FILE}:{file_number}:{file_number}:{offset}:0",
        ),
        translated_button(
            "gf_download", f"{DOWNLOAD_PRODUCTS_CALLBACK}:{file_number}:{offset}"
        ),
    )
    products_delete_buttons(keyboard, file_number, offset, confirmation)
    return keyboard.row(
        translated_button("gl_back", f"{CBT.PRODUCTS_FILES_LIST}:{offset}"),
        translated_button(
            "gl_refresh", f"{CBT.EDIT_PRODUCTS_FILE}:{file_number}:{offset}"
        ),
    )


def lots_list(cardinal: Cardinal, offset: int) -> K:
    keyboard = K()
    lots = cardinal.AD_CFG.sections()[offset : offset + MENU_CFG.AD_BTNS_AMOUNT]
    if not lots and offset != 0:
        offset = 0
        lots = cardinal.AD_CFG.sections()[offset : offset + MENU_CFG.AD_BTNS_AMOUNT]
    for index, lot in enumerate(lots):
        label = compact_button_label(lot, f"{LOT_ICON} ")
        keyboard.add(
            B(label, callback_data=f"{CBT.EDIT_AD_LOT}:{offset + index}:{offset}")
        )
    keyboard = add_navigation_buttons(
        keyboard,
        offset,
        MENU_CFG.AD_BTNS_AMOUNT,
        len(lots),
        len(cardinal.AD_CFG.sections()),
        CBT.AD_LOTS_LIST,
    )
    return delivery_list_footer(keyboard)


def funpay_lots_list(c: Cardinal, offset: int) -> K:
    keyboard = K()
    lots = c.tg_profile.get_common_lots()
    lots = lots[offset : offset + MENU_CFG.FP_LOTS_BTNS_AMOUNT]
    if not lots and offset != 0:
        offset = 0
        lots = c.tg_profile.get_common_lots()[
            offset : offset + MENU_CFG.FP_LOTS_BTNS_AMOUNT
        ]
    for index, lot in enumerate(lots):
        label = compact_button_label(lot.description, f"{LOT_ICON} ")
        keyboard.add(
            B(label, callback_data=f"{CBT.ADD_AD_TO_LOT}:{offset + index}:{offset}")
        )
    keyboard = add_navigation_buttons(
        keyboard,
        offset,
        MENU_CFG.FP_LOTS_BTNS_AMOUNT,
        len(lots),
        len(c.tg_profile.get_common_lots()),
        CBT.FP_LOTS_LIST,
    )
    keyboard.row(
        translated_button("fl_manual", f"{CBT.ADD_AD_TO_LOT_MANUALLY}:{offset}"),
        translated_button("gl_refresh", f"{UPDATE_FUNPAY_LOTS_CALLBACK}:{offset}"),
    )
    return delivery_list_footer(keyboard)


def lot_stock_buttons(keyboard: K, lot_obj, lot_number: int, offset: int) -> K:
    file_name = lot_obj.get("productsFileName")
    link = translated_button(
        "ea_link_goods_file", f"{CBT.BIND_PRODUCTS_FILE}:{lot_number}:{offset}"
    )
    if not file_name:
        return keyboard.add(link)
    if file_name not in os.listdir(PRODUCTS_DIRECTORY):
        with open(f"{PRODUCTS_DIRECTORY}/{file_name}", "w", encoding="utf-8"):
            pass
    file_number = os.listdir(PRODUCTS_DIRECTORY).index(file_name)
    return keyboard.row(
        link,
        translated_button(
            "gf_add_goods",
            f"{CBT.ADD_PRODUCTS_TO_FILE}:{file_number}:{lot_number}:{offset}:1",
        ),
    )


def lot_setting_button(
    c: Cardinal, lot_obj, label: str, global_key: str, setting: str, payload: str
) -> B:
    globally_enabled = c.MAIN_CFG["FunPay"].getboolean(global_key)
    if not globally_enabled:
        return B(
            _module_state._(label, INACTIVE_SETTING_ICON),
            callback_data=CBT.PARAM_DISABLED,
        )
    icon = (
        DISABLED_SETTING_ICON if lot_obj.getboolean(setting) else ENABLED_SETTING_ICON
    )
    return B(
        _module_state._(label, icon),
        callback_data=f"{SWITCH_LOT_CALLBACK}:{setting}:{payload}",
    )


def lot_setting_rows(keyboard: K, c: Cardinal, lot_obj, payload: str) -> K:
    buttons = [
        lot_setting_button(c, lot_obj, *option, payload) for option in LOT_SETTINGS
    ]
    return keyboard.row(*buttons[:2]).row(*buttons[2:])


def edit_lot(c: Cardinal, lot_number: int, offset: int) -> K:
    lot_obj = c.AD_CFG[c.AD_CFG.sections()[lot_number]]
    payload = f"{lot_number}:{offset}"
    keyboard = K().add(
        translated_button(
            "ea_edit_delivery_text", f"{CBT.EDIT_LOT_DELIVERY_TEXT}:{payload}"
        )
    )
    lot_stock_buttons(keyboard, lot_obj, lot_number, offset)
    lot_setting_rows(keyboard, c, lot_obj, payload)
    return keyboard.row(
        translated_button("ea_test", f"{TEST_DELIVERY_CALLBACK}:{payload}"),
        translated_button("gl_delete", f"{CBT.DEL_AD_LOT}:{payload}"),
    ).row(
        translated_button("gl_back", f"{CBT.AD_LOTS_LIST}:{offset}"),
        translated_button("gl_refresh", f"{CBT.EDIT_AD_LOT}:{payload}"),
    )


def templates_list(c: Cardinal, offset: int) -> K:
    keyboard = K()
    templates = c.telegram.answer_templates[
        offset : offset + MENU_CFG.TMPLT_BTNS_AMOUNT
    ]
    if not templates and offset != 0:
        offset = 0
        templates = c.telegram.answer_templates[
            offset : offset + MENU_CFG.TMPLT_BTNS_AMOUNT
        ]
    for index, template in enumerate(templates):
        label = compact_button_label(template, f"{TEMPLATE_ICON} ")
        keyboard.add(
            B(label, callback_data=f"{CBT.EDIT_TMPLT}:{offset + index}:{offset}")
        )
    keyboard = add_navigation_buttons(
        keyboard,
        offset,
        MENU_CFG.TMPLT_BTNS_AMOUNT,
        len(templates),
        len(c.telegram.answer_templates),
        CBT.TMPLT_LIST,
    )
    return keyboard.row(
        translated_button("tmplt_add", f"{CBT.ADD_TMPLT}:{offset}"),
        translated_button("gl_back", CBT.MAIN),
    )


def edit_template(c: Cardinal, template_index: int, offset: int) -> K:
    return (
        K()
        .add(
            translated_button(
                "gl_delete", f"{CBT.DEL_TMPLT}:{template_index}:{offset}"
            ),
        )
        .add(translated_button("gl_back", f"{CBT.TMPLT_LIST}:{offset}"))
    )


def templates_answer_navigation(
    keyboard: K,
    c: Cardinal,
    offset: int,
    count: int,
    node_id: int,
    username: str,
    previous: int,
    extra: list | None,
) -> K:
    parameters = [node_id, username, previous]
    if extra:
        parameters.extend(extra)
    return add_navigation_buttons(
        keyboard,
        offset,
        MENU_CFG.TMPLT_BTNS_AMOUNT,
        count,
        len(c.telegram.answer_templates),
        CBT.TMPLT_LIST_ANS_MODE,
        parameters,
    )


def templates_answer_back(
    keyboard: K, node_id: int, username: str, previous: int, extra: str
) -> K:
    if previous in (0, 1):
        return keyboard.add(
            translated_button(
                "gl_back",
                f"{CBT.BACK_TO_REPLY_KB}:{node_id}:{username}:{previous}{extra}",
            )
        )
    if previous == 2:
        return keyboard.add(
            translated_button(
                "gl_back", f"{CBT.BACK_TO_ORDER_KB}:{node_id}:{username}{extra}"
            )
        )
    return keyboard


def templates_list_ans_mode(
    c: Cardinal,
    offset: int,
    node_id: int,
    username: str,
    prev_page: int,
    extra: list | None = None,
) -> K:
    keyboard = K()
    templates = c.telegram.answer_templates[
        offset : offset + MENU_CFG.TMPLT_BTNS_AMOUNT
    ]
    extra_str = ":" + ":".join(str(value) for value in extra) if extra else ""
    if not templates and offset != 0:
        offset = 0
        templates = c.telegram.answer_templates[
            offset : offset + MENU_CFG.TMPLT_BTNS_AMOUNT
        ]
    for index, template in enumerate(templates):
        label = compact_button_label(
            template.replace("$username", username), f"{TEMPLATE_ICON} "
        )
        payload = f"{CBT.SEND_TMPLT}:{offset + index}:{node_id}:{username}:{prev_page}{extra_str}"
        keyboard.add(B(label, callback_data=payload))
    keyboard = templates_answer_navigation(
        keyboard, c, offset, len(templates), node_id, username, prev_page, extra
    )
    return templates_answer_back(keyboard, node_id, username, prev_page, extra_str)


def new_order(
    order_id: str,
    username: str,
    node_id: int,
    confirmation: bool = False,
    no_refund: bool = False,
) -> K:
    buttons = refund_notification_buttons(
        order_id, username, node_id, confirmation, no_refund
    )
    buttons.extend(
        [
            B(
                _module_state._("ord_open"),
                url=f"https://funpay.com/orders/{order_id}/",
            ),
            translated_button(
                "ord_answer", f"{CBT.SEND_FP_MESSAGE}:{node_id}:{username}"
            ),
            translated_button(
                "ord_templates",
                f"{CBT.TMPLT_LIST_ANS_MODE}:0:{node_id}:{username}:2:{order_id}:{int(no_refund)}",
            ),
        ]
    )
    return notification_keyboard(buttons)


def reply(node_id: int, username: str, again: bool = False, extend: bool = False) -> K:
    bts = reply_notification_buttons(node_id, username, again, extend)
    bts.append(
        B(
            _module_state._("msg_open_chat"),
            url=f"https://funpay.com/chat/?node={node_id}",
        )
    )
    return notification_keyboard(bts)
