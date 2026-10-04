import logging
import time
from threading import Thread

from FunPayAPI.common.enums import OrderStatuses
from cardinal_core.message_results import MessageSendFailure
from locales.localizer import Localizer
from Utils.funpay_time import funpay_now, funpay_timestamp, order_moment
from tg_bot.constants.order_reminder import (
    REMINDER_AUTHOR_ME,
    REMINDER_AUTHOR_OTHER,
    REMINDER_BATCH_LIMIT,
    REMINDER_CHECK_SECONDS,
    REMINDER_FIRST_CHECK_SECONDS,
    REMINDER_LOGGER,
    REMINDER_MAX_AGE_SECONDS,
    REMINDER_ORDER_VARIABLE,
    REMINDER_SEND_PAUSE,
    REMINDER_THREAD_NAME,
    REMINDER_TICK_SECONDS,
    REMINDER_USERNAME_VARIABLE,
)
from tg_bot.order_reminder.store import ReminderStore

logger = logging.getLogger(REMINDER_LOGGER)


def paid_timestamp(order):
    return funpay_timestamp(order_moment(order.date, funpay_now()))


def due_orders(orders, chats, reminded, now, hours, blocked=()):
    blocked = {str(name).casefold() for name in blocked}
    groups = {}
    for order in orders:
        if order.status is not OrderStatuses.PAID or str(order.id) in reminded:
            continue
        name = str(order.buyer_username or "").casefold()
        if not name or name in blocked:
            continue
        paid_at = paid_timestamp(order)
        if now - paid_at > REMINDER_MAX_AGE_SECONDS:
            continue
        chat = chats.get(name)
        if chat is None or chat["author"] != REMINDER_AUTHOR_ME:
            continue
        if chat["time"] < paid_at or now - chat["time"] < hours * 3600:
            continue
        groups.setdefault(name, []).append(order)
    return groups


def render_text(template, username, orders):
    numbers = ", ".join(f"#{order.id}" for order in orders)
    return template.replace(REMINDER_USERNAME_VARIABLE, str(username)).replace(
        REMINDER_ORDER_VARIABLE, numbers
    )


class OrderReminder:
    def __init__(self, cardinal, store=None, clock=time.time, sleep=time.sleep):
        self.cardinal = cardinal
        self.store = store if store is not None else ReminderStore()
        self.clock = clock
        self.sleep = sleep
        self.next_check = clock() + REMINDER_FIRST_CHECK_SECONDS

    def start(self):
        Thread(target=self.loop, name=REMINDER_THREAD_NAME, daemon=True).start()
        return self

    def loop(self):
        while True:
            self.sleep(REMINDER_TICK_SECONDS)
            try:
                self.tick()
            except Exception:
                logger.debug("TRACEBACK", exc_info=True)

    def tick(self):
        now = self.clock()
        if now >= self.next_check:
            self.next_check = now + REMINDER_CHECK_SECONDS
            self.store.prune(now)
            try:
                self.check(now)
            except Exception:
                logger.warning("Не удалось проверить заказы для напоминаний.")
                logger.debug("TRACEBACK", exc_info=True)
        if self.store.dirty:
            self.store.save()

    def observe(self, message):
        name = str(message.chat_name or "").strip().casefold()
        if not name or not message.author_id:
            return
        mine = message.author_id == self.cardinal.account.id
        author = REMINDER_AUTHOR_ME if mine else REMINDER_AUTHOR_OTHER
        self.store.observe(name, message.chat_id, author, self.clock())

    def template(self):
        return self.store.text or Localizer().translate("cr_default_text")

    def check(self, now):
        account = self.cardinal.account
        if not self.store.enabled or not account.is_initiated:
            return 0
        _, orders, _, _ = account.get_sales(state="paid")
        groups = due_orders(
            orders,
            self.store.chats,
            self.store.reminded,
            now,
            self.store.hours,
            getattr(self.cardinal, "blacklist", ()),
        )
        sent = 0
        for index, (name, group) in enumerate(groups.items()):
            if index >= REMINDER_BATCH_LIMIT:
                break
            if index:
                self.sleep(REMINDER_SEND_PAUSE)
            sent += self.send(name, group)
        return sent

    def send(self, name, group):
        first = group[0]
        chat_id = self.store.chats.get(name, {}).get("chat_id") or first.chat_id
        text = render_text(self.template(), first.buyer_username, group)
        result = self.cardinal.send_message(
            chat_id, text, first.buyer_username, first.buyer_id
        )
        self.store.mark([order.id for order in group], self.clock())
        numbers = ", ".join(f"#{order.id}" for order in group)
        if not result or isinstance(result, MessageSendFailure):
            logger.warning(
                "Не удалось напомнить %s о заказе %s.", first.buyer_username, numbers
            )
            return 0
        logger.info("Напомнил %s подтвердить заказ %s.", first.buyer_username, numbers)
        return 1
