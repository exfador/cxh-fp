from html import escape

from telebot.types import InlineKeyboardButton as B
from telebot.types import InlineKeyboardMarkup as K

from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot.constants.chat_sync import (
    CHAT_SYNC_ADD_BOT_URL,
    CHAT_SYNC_BIND_COMMAND,
    CHAT_SYNC_HELPER_GROUP_URL,
    CHAT_SYNC_HISTORY_COMMAND,
    CHAT_SYNC_MESSAGES_PER_BOT,
    CHAT_SYNC_OPTIONS,
)
from tg_bot.utils import bool_to_text


def translate(key, *args):
    return Localizer().translate(key, *args)


def panel_text(service, bot_username):
    lines = [translate("cs_panel_title")]
    report = service.status()
    if report is None:
        lines.append(
            translate("cs_panel_unbound", bot_username, CHAT_SYNC_BIND_COMMAND)
        )
        if service.cardinal.old_mode_enabled:
            lines.append(f"⚠️ {translate('cs_problem_old_mode')}")
        return "\n\n".join(lines)
    block = [
        translate("cs_panel_group", escape(service.store.title or "—"), service.chat_id)
    ]
    if report["problems"]:
        problems = service.problems_text(report["problems"])
        block.append(f"{translate('cs_panel_problems')}\n{problems}")
    else:
        block.append(translate("cs_panel_ok"))
    block.append(translate("cs_panel_topics", len(service.store.threads)))
    if service.syncing:
        block.append(translate("cs_panel_syncing"))
    lines.append("<blockquote>" + "\n".join(block) + "</blockquote>")
    lines.append(translate("cs_panel_usage", CHAT_SYNC_HISTORY_COMMAND))
    return "\n\n".join(lines)


def toggle_button(label, action):
    return B(label, callback_data=f"{CBT.CHAT_SYNC_TOGGLE}:{action}")


def panel_keyboard(service, bot_username):
    keyboard = K()
    refresh = toggle_button(translate("gl_refresh"), "refresh")
    if not service.active():
        if bot_username:
            keyboard.row(
                B(
                    translate("cs_add_bot_button"),
                    url=CHAT_SYNC_ADD_BOT_URL.format(bot_username),
                )
            )
        return keyboard.row(refresh)
    for key, label in CHAT_SYNC_OPTIONS:
        state = bool_to_text(service.store.option(key))
        keyboard.row(toggle_button(f"{state} {translate(label)}", key))
    keyboard.row(toggle_button(translate("cs_sync_button"), "sync"))
    keyboard.row(
        B(
            translate("cs_helpers_button", len(service.store.helpers)),
            callback_data=CBT.CHAT_SYNC_HELPERS,
        )
    )
    return keyboard.row(
        refresh,
        B(translate("cs_unbind_button"), callback_data=CBT.CHAT_SYNC_UNBIND),
    )


def unbind_keyboard():
    return K().row(
        B(translate("cs_unbind_yes"), callback_data=CBT.CHAT_SYNC_UNBIND_CONFIRM),
        toggle_button(translate("cs_unbind_no"), "refresh"),
    )


def helpers_text(statuses):
    lines = [translate("cs_helpers_title"), translate("cs_helpers_about")]
    bots = len(statuses) + 1
    lines.append(translate("cs_helpers_speed", bots, bots * CHAT_SYNC_MESSAGES_PER_BOT))
    if statuses:
        lines.append(
            "\n".join(
                f"{index}. @{escape(lane.username or str(lane.user_id))}: "
                f"{translate(f'cs_helper_status_{status}')}"
                for index, (lane, status) in enumerate(statuses, start=1)
            )
        )
    else:
        lines.append(translate("cs_helpers_empty"))
    lines.append(translate("cs_helpers_howto"))
    return "\n\n".join(lines)


def helper_group_button(username):
    return B(
        translate("cs_helper_to_group", username),
        url=CHAT_SYNC_HELPER_GROUP_URL.format(username),
    )


def helpers_keyboard(statuses):
    keyboard = K()
    for lane, status in statuses:
        row = []
        if lane.username and status in ("missing", "send"):
            row.append(helper_group_button(lane.username))
        elif lane.username:
            row.append(B(f"@{lane.username}", url=f"https://t.me/{lane.username}"))
        row.append(
            B(
                translate("cs_helper_remove", lane.username or lane.user_id),
                callback_data=f"{CBT.CHAT_SYNC_HELPER_DEL}:{lane.user_id}",
            )
        )
        keyboard.row(*row)
    keyboard.row(
        B(translate("cs_helper_add_button"), callback_data=CBT.CHAT_SYNC_HELPER_ADD)
    )
    return keyboard.row(
        B(translate("gl_refresh"), callback_data=CBT.CHAT_SYNC_HELPERS_REFRESH)
    )


def helper_result_keyboard(username):
    keyboard = K()
    if username:
        keyboard.row(helper_group_button(username))
    return keyboard.row(
        B(translate("cs_helper_back"), callback_data=CBT.CHAT_SYNC_HELPERS_REFRESH)
    )
