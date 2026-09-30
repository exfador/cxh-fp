from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from FunPayAPI.types import Order
from FunPayAPI.updater.events import *
from tg_bot import utils, keyboards
from app.constants.branding import BRAND_ICON
from Utils import cardinal_tools
from threading import Thread
import time
import handlers as _module_state
from Utils.logging_support.constants.private_content import CHAT_CONTENT_METADATA


def save_init_chats_handler(c: Cardinal, e: InitialChatEvent):
    if (
        c.MAIN_CFG["Greetings"].getboolean("sendGreetings")
        and e.chat.id not in c.old_users
    ):
        c.old_users[e.chat.id] = int(time.time())
        cardinal_tools.cache_old_users(c.old_users)


def update_threshold_on_initial_chat(c: Cardinal, e: InitialChatEvent):
    if e.chat.id > c.greeting_chat_id_threshold:
        c.greeting_chat_id_threshold = e.chat.id


def old_log_msg_handler(c: Cardinal, e: LastChatMessageChangedEvent):
    if not c.old_mode_enabled:
        return
    _module_state.logger.info(CHAT_CONTENT_METADATA, e.chat.id, 1, len(str(e.chat)))


def log_msg_handler(c: Cardinal, e: NewMessageEvent):
    if e.stack.id() == _module_state.MSG_LOG_LAST_STACK_ID:
        return
    events = e.stack.get_stack()
    character_count = sum(len(event.message.text or "") for event in events)
    _module_state.logger.info(
        CHAT_CONTENT_METADATA, e.message.chat_id, len(events), character_count
    )
    _module_state.MSG_LOG_LAST_STACK_ID = e.stack.id()


def update_threshold_on_last_message_change(
    c: Cardinal, e: LastChatMessageChangedEvent | NewMessageEvent
):
    if not c.old_mode_enabled:
        if isinstance(e, LastChatMessageChangedEvent):
            return
        chat_id = e.message.chat_id
    else:
        chat_id = e.chat.id
    if e.runner_tag != c.last_greeting_chat_id_threshold_change_tag:
        c.greeting_chat_id_threshold = max(
            [c.greeting_chat_id_threshold, *c.greeting_threshold_chat_ids]
        )
        c.greeting_threshold_chat_ids = set()
        c.last_greeting_chat_id_threshold_change_tag = e.runner_tag
    c.greeting_threshold_chat_ids.add(chat_id)


def greetings_handler(c: Cardinal, e: NewMessageEvent | LastChatMessageChangedEvent):
    if not c.MAIN_CFG["Greetings"].getboolean("sendGreetings"):
        return
    if not c.old_mode_enabled:
        if isinstance(e, LastChatMessageChangedEvent):
            return
        obj = e.message
        chat_id, chat_name, mtype, its_me, badge = (
            obj.chat_id,
            obj.chat_name,
            obj.type,
            obj.author_id == c.account.id,
            obj.badge,
        )
    else:
        obj = e.chat
        chat_id, chat_name, mtype, its_me, badge = (
            obj.id,
            obj.name,
            obj.last_message_type,
            not obj.unread,
            None,
        )
    is_old_chat = (
        chat_id <= c.greeting_chat_id_threshold
        or chat_id in c.greeting_threshold_chat_ids
    )
    if any(
        [
            c.MAIN_CFG["Greetings"].getboolean("onlyNewChats") and is_old_chat,
            time.time() - c.old_users.get(chat_id, 0)
            < float(c.MAIN_CFG["Greetings"]["greetingsCooldown"]) * 24 * 60 * 60,
            its_me,
            mtype in (MessageTypes.DEAR_VENDORS, MessageTypes.ORDER_CONFIRMED_BY_ADMIN),
            badge is not None,
            mtype is not MessageTypes.NON_SYSTEM
            and c.MAIN_CFG["Greetings"].getboolean("ignoreSystemMessages"),
        ]
    ):
        return
    _module_state.logger.info(
        _module_state._("log_sending_greetings", chat_name, chat_id)
    )
    text = cardinal_tools.format_msg_text(c.MAIN_CFG["Greetings"]["greetingsText"], obj)
    Thread(target=c.send_message, args=(chat_id, text, chat_name), daemon=True).start()


def add_old_user_handler(c: Cardinal, e: NewMessageEvent | LastChatMessageChangedEvent):
    if not c.MAIN_CFG["Greetings"].getboolean("sendGreetings") or c.MAIN_CFG[
        "Greetings"
    ].getboolean("onlyNewChats"):
        return
    if not c.old_mode_enabled:
        if isinstance(e, LastChatMessageChangedEvent):
            return
        chat_id, mtype = (e.message.chat_id, e.message.type)
    else:
        chat_id, mtype = (e.chat.id, e.chat.last_message_type)
    if mtype == MessageTypes.DEAR_VENDORS:
        return
    c.old_users[chat_id] = int(time.time())
    cardinal_tools.cache_old_users(c.old_users)


def send_response_handler(
    c: Cardinal, e: NewMessageEvent | LastChatMessageChangedEvent
):
    if not c.autoresponse_enabled:
        return
    if not c.old_mode_enabled:
        if isinstance(e, LastChatMessageChangedEvent):
            return
        obj, mtext = (e.message, str(e.message))
        chat_id, chat_name, username = (
            e.message.chat_id,
            e.message.chat_name,
            e.message.author,
        )
    else:
        obj, mtext = (e.chat, str(e.chat))
        chat_id, chat_name, username = (obj.id, obj.name, obj.name)
    mtext = mtext.replace("\n", "")
    if any(
        [
            c.bl_response_enabled and username in c.blacklist,
            (command := mtext.strip().lower()) not in c.AR_CFG,
        ]
    ):
        return
    if not c.AR_CFG[command].getboolean("enabled"):
        return
    _module_state.logger.info(
        _module_state._("log_new_cmd", command, chat_name, chat_id)
    )
    response_text = cardinal_tools.format_msg_text(c.AR_CFG[command]["response"], obj)
    Thread(
        target=c.send_message, args=(chat_id, response_text, chat_name), daemon=True
    ).start()


def old_send_new_msg_notification_handler(c: Cardinal, e: LastChatMessageChangedEvent):
    if any(
        [
            not c.old_mode_enabled,
            not c.telegram,
            not e.chat.unread,
            c.bl_msg_notification_enabled and e.chat.name in c.blacklist,
            e.chat.last_message_type is not MessageTypes.NON_SYSTEM,
            str(e.chat).strip().lower() in c.AR_CFG.sections(),
            str(e.chat).startswith("!автовыдача"),
        ]
    ):
        return
    user = e.chat.name
    if user in c.blacklist:
        user = f"🚷 {user}"
    elif e.chat.last_by_bot:
        user = f"{BRAND_ICON} {user}"
    else:
        user = f"👤 {user}"
    text = f"<b>{utils.escape(user)}</b>\n{utils.escape(str(e.chat))}"
    kb = keyboards.reply(e.chat.id, e.chat.name, extend=True)
    Thread(
        target=c.telegram.send_notification,
        args=(text, kb, utils.NotificationTypes.new_message),
        daemon=True,
    ).start()


def send_new_msg_notification_handler(c: Cardinal, e: NewMessageEvent) -> None:
    if not c.telegram or e.stack.id() == _module_state.LAST_STACK_ID:
        return
    _module_state.LAST_STACK_ID = e.stack.id()
    chat_id, chat_name = (e.message.chat_id, e.message.chat_name)
    if c.bl_msg_notification_enabled and chat_name in c.blacklist:
        return
    events = []
    nm, m, f, b = (False, False, False, False)
    for i in e.stack.get_stack():
        if i.message.author_id == 0:
            if c.include_fp_msg_enabled:
                events.append(i)
                f = True
        elif i.message.by_bot:
            if c.include_bot_msg_enabled:
                events.append(i)
                b = True
        elif i.message.author_id == c.account.id:
            if c.include_my_msg_enabled:
                events.append(i)
                m = True
        else:
            events.append(i)
            nm = True
    if not events:
        return
    if [m, f, b, nm].count(True) == 1 and any(
        [
            m and (not c.only_my_msg_enabled),
            f and (not c.only_fp_msg_enabled),
            b and (not c.only_bot_msg_enabled),
        ]
    ):
        return
    if len(events) < 2:
        message_text = str(e.message)
        if (
            message_text.strip().lower() in c.AR_CFG.sections()
            or message_text.startswith("!автовыдача")
        ):
            return
    text = utils.format_messages(c, [i.message for i in events])
    kb = keyboards.reply(chat_id, chat_name, extend=True)
    Thread(
        target=c.telegram.send_notification,
        args=(text, kb, utils.NotificationTypes.new_message),
        daemon=True,
    ).start()


def send_review_notification(
    c: Cardinal, order: Order, chat_id: int, reply_text: str | None
):
    if not c.telegram:
        return
    reply_text = (
        _module_state._("ntfc_review_reply_text").format(utils.escape(reply_text))
        if reply_text
        else ""
    )
    Thread(
        target=c.telegram.send_notification,
        args=(
            _module_state._("ntfc_new_review").format(
                "⭐" * order.review.stars,
                order.id,
                utils.escape(order.review.text),
                reply_text,
            ),
            keyboards.new_order(order.id, order.buyer_username, chat_id),
            utils.NotificationTypes.review,
        ),
        daemon=True,
    ).start()
