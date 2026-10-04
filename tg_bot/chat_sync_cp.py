from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telebot.types import CallbackQuery, Message

from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot import static_keyboards as skb
from tg_bot.chat_sync.service import ChatSyncService
from tg_bot.constants.chat_sync import (
    CHAT_SYNC_BIND_COMMAND,
    CHAT_SYNC_GROUP_PREFIX,
    CHAT_SYNC_HELPER_LIMIT,
    CHAT_SYNC_HISTORY_COMMAND,
    CHAT_SYNC_OUTGOING_TYPES,
    CHAT_SYNC_TELEBOT_LOGGER,
    CHAT_SYNC_TELEBOT_NOISE,
)
from tg_bot.keyboard_views.chat_sync import (
    helper_result_keyboard,
    helpers_keyboard,
    helpers_text,
    panel_keyboard,
    panel_text,
    unbind_keyboard,
)

if TYPE_CHECKING:
    from cardinal import Cardinal

logger = logging.getLogger("CoxerHubBot.chat_sync")
_ = Localizer().translate


def quiet_permission_warning(record):
    return CHAT_SYNC_TELEBOT_NOISE not in record.getMessage()


def guarded(function):
    def run(update):
        try:
            function(update)
        except Exception:
            logger.error("Ошибка синхронизации чатов в Telegram.")
            logger.debug("TRACEBACK", exc_info=True)

    return run


def register_group_handlers(bot, service):
    bot.register_my_chat_member_handler(guarded(service.membership))
    bot.register_message_handler(
        guarded(service.bind_command),
        commands=[CHAT_SYNC_BIND_COMMAND],
        chat_types=["group", "supergroup"],
    )
    bot.register_message_handler(
        guarded(service.history_command),
        commands=[CHAT_SYNC_HISTORY_COMMAND],
        func=lambda message: service.target(message) is not None,
    )
    bot.register_message_handler(
        guarded(service.queue_outgoing),
        content_types=list(CHAT_SYNC_OUTGOING_TYPES),
        func=service.outgoing_wanted,
    )
    bot.register_callback_query_handler(
        guarded(service.callback),
        func=lambda call: (call.data or "").startswith(f"{CHAT_SYNC_GROUP_PREFIX}:"),
    )


def init_chat_sync_cp(crd: Cardinal, *args):
    tg = crd.telegram
    bot = tg.bot
    service = ChatSyncService(crd, bot)
    tg.chat_sync = service
    telebot_logger = logging.getLogger(CHAT_SYNC_TELEBOT_LOGGER)
    if quiet_permission_warning not in telebot_logger.filters:
        telebot_logger.addFilter(quiet_permission_warning)

    def bot_username():
        try:
            return bot.user.username
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            return ""

    def render(c: CallbackQuery):
        username = bot_username()
        bot.edit_message_text(
            panel_text(service, username),
            c.message.chat.id,
            c.message.id,
            reply_markup=panel_keyboard(service, username),
        )

    def open_panel(c: CallbackQuery):
        render(c)
        bot.answer_callback_query(c.id)

    def toggle(c: CallbackQuery):
        action = c.data.split(":", 1)[1]
        note = None
        if action == "sync":
            note = _("cs_sync_started" if service.start_sync() else "cs_sync_running")
        elif action != "refresh":
            service.store.toggle(action)
        render(c)
        bot.answer_callback_query(c.id, note)

    def ask_unbind(c: CallbackQuery):
        bot.edit_message_text(
            _("cs_unbind_confirm"),
            c.message.chat.id,
            c.message.id,
            reply_markup=unbind_keyboard(),
        )
        bot.answer_callback_query(c.id)

    def unbind(c: CallbackQuery):
        service.unbind()
        render(c)
        bot.answer_callback_query(c.id, _("cs_unbound_done"))

    tg.cbq_handler(open_panel, lambda c: c.data == CBT.CHAT_SYNC)
    tg.cbq_handler(toggle, lambda c: c.data.startswith(f"{CBT.CHAT_SYNC_TOGGLE}:"))
    tg.cbq_handler(ask_unbind, lambda c: c.data == CBT.CHAT_SYNC_UNBIND)
    tg.cbq_handler(unbind, lambda c: c.data == CBT.CHAT_SYNC_UNBIND_CONFIRM)
    register_group_handlers(bot, service)
    register_helper_handlers(tg, service)


def register_helper_handlers(tg, service):
    bot = tg.bot

    def render_helpers(c: CallbackQuery, note=None):
        statuses = service.refresh_helpers()
        bot.edit_message_text(
            helpers_text(statuses),
            c.message.chat.id,
            c.message.id,
            reply_markup=helpers_keyboard(statuses),
        )
        bot.answer_callback_query(c.id, note)

    def remove_helper(c: CallbackQuery):
        user_id = c.data.split(":", 1)[1]
        removed = service.remove_helper(int(user_id)) if user_id.isdigit() else None
        render_helpers(c, _("cs_helper_removed") if removed else None)

    def ask_token(c: CallbackQuery):
        result = bot.send_message(
            c.message.chat.id,
            _("cs_helper_prompt"),
            reply_markup=skb.CLEAR_STATE_BTN(),
        )
        tg.set_state(
            c.message.chat.id, result.id, c.from_user.id, CBT.CHAT_SYNC_HELPER_ADD
        )
        bot.answer_callback_query(c.id)

    def receive_token(m: Message):
        try:
            bot.delete_message(m.chat.id, m.message_id)
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
        tg.clear_state(m.chat.id, m.from_user.id, True)
        error, username = service.add_helper(m.text or "")
        if error:
            text = _(error, CHAT_SYNC_HELPER_LIMIT)
        else:
            text = _("cs_helper_added", username)
        bot.send_message(m.chat.id, text, reply_markup=helper_result_keyboard(username))

    tg.cbq_handler(
        render_helpers,
        lambda c: c.data in (CBT.CHAT_SYNC_HELPERS, CBT.CHAT_SYNC_HELPERS_REFRESH),
    )
    tg.cbq_handler(
        remove_helper, lambda c: c.data.startswith(f"{CBT.CHAT_SYNC_HELPER_DEL}:")
    )
    tg.cbq_handler(ask_token, lambda c: c.data == CBT.CHAT_SYNC_HELPER_ADD)
    tg.msg_handler(
        receive_token,
        content_types=["text"],
        func=lambda m: tg.check_state(
            m.chat.id, m.from_user.id, CBT.CHAT_SYNC_HELPER_ADD
        ),
    )


BIND_TO_PRE_INIT = [init_chat_sync_cp]
