import logging
import time
from threading import Thread

import requests

from FunPayAPI.common import exceptions
from locales.localizer import Localizer
from Utils.cardinal_tools import time_to_str
from tg_bot.constants.connection import (
    CONNECTION_AUTH_SECONDS,
    CONNECTION_CHECK_SECONDS,
    CONNECTION_DATE_FORMAT,
    CONNECTION_DOWN_SECONDS,
    CONNECTION_LOGGER,
    CONNECTION_REASONS,
    CONNECTION_THREAD_NAME,
    CONNECTION_TIME_FORMAT,
)
from tg_bot.utils import NotificationTypes

logger = logging.getLogger(CONNECTION_LOGGER)


def failure_kind(error):
    if isinstance(error, exceptions.UnauthorizedError):
        return "auth"
    if isinstance(error, exceptions.RequestFailedError):
        return "server"
    if isinstance(error, (requests.RequestException, TimeoutError, OSError)):
        return "network"
    return "other"


def clock_text(moment, now):
    same_day = time.localtime(moment)[:3] == time.localtime(now)[:3]
    pattern = CONNECTION_TIME_FORMAT if same_day else CONNECTION_DATE_FORMAT
    return time.strftime(pattern, time.localtime(moment))


def duration_text(seconds, translate):
    minutes = max(60, int(seconds) - int(seconds) % 60)
    return time_to_str(minutes, tuple(translate("menu_uptime_units").split()))


class ConnectionMonitor:
    def __init__(self, cardinal, clock=time.time, sleep=time.sleep):
        self.cardinal = cardinal
        self.clock = clock
        self.sleep = sleep
        self.reported = "ok"
        self.incident = None
        self.pending = None

    def start(self):
        Thread(target=self.loop, name=CONNECTION_THREAD_NAME, daemon=True).start()
        return self

    def loop(self):
        while True:
            self.sleep(CONNECTION_CHECK_SECONDS)
            try:
                self.check()
            except Exception:
                logger.debug("TRACEBACK", exc_info=True)

    def evaluate(self, now):
        account = self.cardinal.account
        ok_at = getattr(account, "link_ok_time", now)
        error = getattr(account, "link_error", None)
        failing = error is not None and getattr(account, "link_error_time", 0) > ok_at
        kind = failure_kind(error) if failing else "stalled"
        silent = now - ok_at
        if kind == "auth" and silent >= CONNECTION_AUTH_SECONDS:
            return "auth", ok_at, kind
        if silent >= CONNECTION_DOWN_SECONDS:
            return "down", ok_at, kind
        return "ok", ok_at, kind

    def check(self):
        now = self.clock()
        state, since, kind = self.evaluate(now)
        if state == "ok":
            if self.incident is not None:
                self.pending = self.restored_text(self.incident, now)
                self.incident = None
                self.reported = "ok"
            if self.pending and self.notify(self.pending):
                self.pending = None
            return
        if self.incident is None:
            self.incident = since
            self.pending = None
            logger.warning(
                "Нет связи с FunPay с %s (%s).", clock_text(since, now), kind
            )
        if state != self.reported and self.notify(
            self.problem_text(state, kind, since, now), state == "auth"
        ):
            self.reported = state

    def problem_text(self, state, kind, since, now):
        translate = Localizer().translate
        if state == "auth":
            return translate("conn_auth", clock_text(since, now))
        return translate(
            "conn_down",
            duration_text(now - since, translate),
            clock_text(since, now),
            translate(CONNECTION_REASONS.get(kind, "conn_reason_other")),
        )

    def restored_text(self, since, now):
        translate = Localizer().translate
        logger.info("Связь с FunPay восстановлена.")
        return translate(
            "conn_restored",
            duration_text(now - since, translate),
            clock_text(since, now),
            clock_text(now, now),
        )

    def keyboard(self, auth):
        if not auth:
            return None
        from telebot.types import InlineKeyboardMarkup
        from tg_bot.keyboard_views.operator import operator_button

        return InlineKeyboardMarkup().row(
            operator_button("operator_change_key", "change_key")
        )

    def recipients(self, telegram):
        for chat_id in list(telegram.notification_settings):
            if telegram.notification_recipient_allowed(
                chat_id
            ) and telegram.is_notification_enabled(
                chat_id, NotificationTypes.connection
            ):
                yield int(chat_id)

    def notify(self, text, auth=False):
        telegram = getattr(self.cardinal, "telegram", None)
        if telegram is None:
            return True
        attempted = delivered = False
        for chat_id in self.recipients(telegram):
            attempted = True
            try:
                telegram.bot.send_message(
                    chat_id, text, reply_markup=self.keyboard(auth)
                )
                delivered = True
            except Exception:
                logger.debug("TRACEBACK", exc_info=True)
        return delivered or not attempted
