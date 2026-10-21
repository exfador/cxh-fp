from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from telebot.types import CallbackQuery, Message

from locales.localizer import Localizer
from tg_bot import CBT
from tg_bot import static_keyboards as skb
from tg_bot.constants.review_reminder import (
    REVIEW_REMINDER_LOGGER,
    REVIEW_REMINDER_MAX_HOURS,
    REVIEW_REMINDER_MIN_HOURS,
    REVIEW_REMINDER_TEXT_LIMIT,
)
from tg_bot.keyboard_views.review_reminder import (
    review_reminder_keyboard,
    review_reminder_text,
)
from tg_bot.review_reminder.service import ReviewReminder

if TYPE_CHECKING:
    from cardinal import Cardinal

logger = logging.getLogger(REVIEW_REMINDER_LOGGER)


def translate(key, *args):
    return Localizer().translate(key, *args)


def parse_hours(text):
    value = (text or "").strip()
    if not value.isascii() or not value.isdigit():
        return None
    hours = int(value)
    return (
        hours
        if REVIEW_REMINDER_MIN_HOURS <= hours <= REVIEW_REMINDER_MAX_HOURS
        else None
    )


def parse_text(text):
    value = (text or "").strip()
    return value if value and len(value) <= REVIEW_REMINDER_TEXT_LIMIT else None


def init_review_reminder_cp(crd: Cardinal, *args):
    tg = crd.telegram
    bot = tg.bot
    service = ReviewReminder(crd).start()
    tg.review_reminder = service

    def render(c: CallbackQuery, note=None):
        bot.edit_message_text(
            review_reminder_text(service, time.time()),
            c.message.chat.id,
            c.message.id,
            reply_markup=review_reminder_keyboard(service),
        )
        bot.answer_callback_query(c.id, note)

    def open_panel(c: CallbackQuery):
        render(c)

    def toggle(c: CallbackQuery):
        enabled = not service.store.enabled
        service.store.update(enabled=enabled)
        logger.info(
            "@%s (ID: %s) %s напоминание об отзыве.",
            c.from_user.username,
            c.from_user.id,
            "включил" if enabled else "выключил",
        )
        render(c)

    def reset(c: CallbackQuery):
        service.store.update(text="")
        render(c, translate("cr_text_reset_done"))

    def ask(c: CallbackQuery, state, prompt):
        result = bot.send_message(
            c.message.chat.id, prompt, reply_markup=skb.CLEAR_STATE_BTN()
        )
        tg.set_state(c.message.chat.id, result.id, c.from_user.id, state)
        bot.answer_callback_query(c.id)

    def ask_hours(c: CallbackQuery):
        prompt = translate(
            "rv_hours_prompt", REVIEW_REMINDER_MIN_HOURS, REVIEW_REMINDER_MAX_HOURS
        )
        ask(c, CBT.REVIEW_REMINDER_HOURS, prompt)

    def ask_text(c: CallbackQuery):
        prompt = translate("rv_text_prompt", REVIEW_REMINDER_TEXT_LIMIT)
        ask(c, CBT.REVIEW_REMINDER_TEXT, prompt)

    def show_panel(m: Message, note):
        text = f"{note}\n\n{review_reminder_text(service, time.time())}"
        bot.send_message(
            m.chat.id, text, reply_markup=review_reminder_keyboard(service)
        )

    def retry(m: Message, note):
        bot.send_message(m.chat.id, note, reply_markup=skb.CLEAR_STATE_BTN())

    def receive_hours(m: Message):
        hours = parse_hours(m.text)
        if hours is None:
            retry(
                m,
                translate(
                    "cr_hours_invalid",
                    REVIEW_REMINDER_MIN_HOURS,
                    REVIEW_REMINDER_MAX_HOURS,
                ),
            )
            return
        tg.clear_state(m.chat.id, m.from_user.id, True)
        service.store.update(hours=hours)
        show_panel(m, translate("rv_hours_saved", hours))

    def receive_text(m: Message):
        text = parse_text(m.text)
        if text is None:
            retry(m, translate("cr_text_invalid", REVIEW_REMINDER_TEXT_LIMIT))
            return
        tg.clear_state(m.chat.id, m.from_user.id, True)
        service.store.update(text=text)
        show_panel(m, translate("cr_text_saved"))

    def waiting(state):
        return lambda m: tg.check_state(m.chat.id, m.from_user.id, state)

    tg.cbq_handler(open_panel, lambda c: c.data == CBT.REVIEW_REMINDER)
    tg.cbq_handler(toggle, lambda c: c.data == CBT.REVIEW_REMINDER_TOGGLE)
    tg.cbq_handler(reset, lambda c: c.data == CBT.REVIEW_REMINDER_RESET)
    tg.cbq_handler(ask_hours, lambda c: c.data == CBT.REVIEW_REMINDER_HOURS)
    tg.cbq_handler(ask_text, lambda c: c.data == CBT.REVIEW_REMINDER_TEXT)
    tg.msg_handler(
        receive_hours,
        content_types=["text"],
        func=waiting(CBT.REVIEW_REMINDER_HOURS),
    )
    tg.msg_handler(
        receive_text,
        content_types=["text"],
        func=waiting(CBT.REVIEW_REMINDER_TEXT),
    )


BIND_TO_PRE_INIT = [init_review_reminder_cp]
