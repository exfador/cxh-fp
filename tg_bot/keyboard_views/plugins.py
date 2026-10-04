from __future__ import annotations

from typing import TYPE_CHECKING

from telebot.types import InlineKeyboardButton as B
from telebot.types import InlineKeyboardMarkup as K

import tg_bot.keyboards as _module_state
from tg_bot import CBT, MENU_CFG
from tg_bot.constants.message_sections import (
    DISABLED_SETTING_ICON,
    ENABLED_SETTING_ICON,
    PINNED_PLUGIN_ICON,
    PLUGIN_ICON,
)
from tg_bot.keyboard_views.messages import compact_button_label, translated_button
from tg_bot.promotion import plugin_store_keyboard
from tg_bot.utils import add_navigation_buttons, bool_to_text

if TYPE_CHECKING:
    from cardinal import Cardinal


def plugin_button(plugin, uuid: str, offset: int) -> B:
    icon = PINNED_PLUGIN_ICON if plugin.pinned else PLUGIN_ICON
    label = compact_button_label(
        plugin.name, f"{icon} ", f" {bool_to_text(plugin.enabled)}"
    )
    return B(label, callback_data=f"{CBT.EDIT_PLUGIN}:{uuid}:{offset}")


def broken_plugin_button(entry, offset: int) -> B:
    label = compact_button_label(entry.name, "⚠️ ")
    return B(label, callback_data=f"{CBT.PLUGIN_BROKEN}:{entry.key}:{offset}")


def plugin_entries(c: Cardinal) -> list:
    plugins = sorted(
        c.plugins.keys(),
        key=lambda uuid: (not c.plugins[uuid].pinned, c.plugins[uuid].name.lower()),
    )
    broken = sorted(
        getattr(c, "broken_plugins", {}).values(), key=lambda item: item.name.lower()
    )
    return [("plugin", uuid) for uuid in plugins] + [
        ("broken", item) for item in broken
    ]


def plugins_list(c: Cardinal, offset: int) -> K:
    keyboard = K()
    entries = plugin_entries(c)
    page = entries[offset : offset + MENU_CFG.PLUGINS_BTNS_AMOUNT]
    if not page and offset != 0:
        offset = 0
        page = entries[: MENU_CFG.PLUGINS_BTNS_AMOUNT]
    for kind, item in page:
        if kind == "plugin":
            keyboard.add(plugin_button(c.plugins[item], item, offset))
        else:
            keyboard.add(broken_plugin_button(item, offset))
    keyboard = add_navigation_buttons(
        keyboard,
        offset,
        MENU_CFG.PLUGINS_BTNS_AMOUNT,
        len(page),
        len(entries),
        CBT.PLUGINS_LIST,
    )
    panel = c.telegram is not None and c.telegram.plugin_panel_enabled()
    keyboard.row(
        B(
            _module_state._(
                "pl_panel_mode",
                ENABLED_SETTING_ICON if panel else DISABLED_SETTING_ICON,
            ),
            callback_data=f"{CBT.PLUGIN_PANEL}:{offset}",
        )
    )
    return plugin_store_keyboard(
        keyboard.row(
            translated_button("pl_add", f"{CBT.UPLOAD_PLUGIN}:{offset}"),
            translated_button("gl_back", CBT.MAIN),
        )
    )


def plugin_optional_buttons(keyboard: K, plugin, payload: str) -> K:
    buttons = []
    if plugin.commands:
        buttons.append(
            translated_button("pl_commands", f"{CBT.PLUGIN_COMMANDS}:{payload}")
        )
    if plugin.settings_page:
        buttons.append(
            translated_button("pl_settings", f"{CBT.PLUGIN_SETTINGS}:{payload}")
        )
    if buttons:
        keyboard.row(*buttons)
    return keyboard


def plugin_delete_buttons(keyboard: K, payload: str, confirmation: bool) -> K:
    if not confirmation:
        return keyboard.add(
            translated_button("gl_delete", f"{CBT.DELETE_PLUGIN}:{payload}")
        )
    return keyboard.row(
        translated_button("gl_yes", f"{CBT.CONFIRM_DELETE_PLUGIN}:{payload}"),
        translated_button("gl_no", f"{CBT.CANCEL_DELETE_PLUGIN}:{payload}"),
    )


def broken_plugin(entry, offset: int, ask_to_delete: bool = False) -> K:
    payload = f"{entry.key}:{offset}"
    keyboard = K().add(
        translated_button("plugin_broken_retry", f"{CBT.PLUGIN_BROKEN_RETRY}:{payload}")
    )
    if ask_to_delete:
        keyboard.row(
            translated_button("gl_yes", f"{CBT.PLUGIN_BROKEN_CONFIRM}:{payload}"),
            translated_button("gl_no", f"{CBT.PLUGIN_BROKEN}:{payload}"),
        )
    else:
        keyboard.add(
            translated_button("gl_delete", f"{CBT.PLUGIN_BROKEN_DELETE}:{payload}")
        )
    return keyboard.add(translated_button("gl_back", f"{CBT.PLUGINS_LIST}:{offset}"))


def edit_plugin(c: Cardinal, uuid: str, offset: int, ask_to_delete: bool = False) -> K:
    plugin = c.plugins[uuid]
    payload = f"{uuid}:{offset}"
    active_key = "pl_deactivate" if plugin.enabled else "pl_activate"
    pin_key = "pl_unpin" if plugin.pinned else "pl_pin"
    keyboard = K().row(
        translated_button(active_key, f"{CBT.TOGGLE_PLUGIN}:{payload}"),
        translated_button(pin_key, f"{CBT.PIN_PLUGIN}:{payload}"),
    )
    plugin_optional_buttons(keyboard, plugin, payload)
    plugin_delete_buttons(keyboard, payload, ask_to_delete)
    return keyboard.add(translated_button("gl_back", f"{CBT.PLUGINS_LIST}:{offset}"))
