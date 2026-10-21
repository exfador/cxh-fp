import logging
import time
from threading import Thread

from FunPayAPI.common.enums import MessageTypes, OrderStatuses
from FunPayAPI.common.utils import RegularExpressions
from cardinal_core.message_results import MessageSendFailure
from locales.localizer import Localizer
from tg_bot.constants.review_reminder import (
    REVIEW_REMINDER_BATCH_LIMIT,
    REVIEW_REMINDER_CHECK_SECONDS,
    REVIEW_REMINDER_FIRST_CHECK_SECONDS,
    REVIEW_REMINDER_LOGGER,
    REVIEW_REMINDER_MAX_AGE_SECONDS,
    REVIEW_REMINDER_ORDER_LIMIT,
    REVIEW_REMINDER_ORDER_VARIABLE,
    REVIEW_REMINDER_SEND_PAUSE,
    REVIEW_REMINDER_THREAD_NAME,
    REVIEW_REMINDER_TICK_SECONDS,
    REVIEW_REMINDER_USERNAME_VARIABLE,
    REVIEW_STATUS_FAILED,
    REVIEW_STATUS_REVIEWED,
    REVIEW_STATUS_SENT,
    REVIEW_STATUS_SKIPPED,
)
from tg_bot.review_reminder.store import ReviewReminderStore

logger = logging.getLogger(REVIEW_REMINDER_LOGGER)
REVIEW_TYPES = frozenset({MessageTypes.NEW_FEEDBACK, MessageTypes.FEEDBACK_CHANGED})


def due_reviews(pending, now, hours, blocked=()):
    blocked = {str(name).casefold() for name in blocked}
    groups = {}
    for order_id, entry in sorted(pending.items(), key=lambda item: item[1]["time"]):
        name = entry["buyer"].casefold()
        if name in blocked:
            continue
        age = now - entry["time"]
        if age < hours * 3600 or age > REVIEW_REMINDER_MAX_AGE_SECONDS:
            continue
        groups.setdefault(name, []).append(order_id)
    return groups


def blocked_orders(pending, blocked):
    blocked = {str(name).casefold() for name in blocked}
    return [
        key for key, entry in pending.items() if entry["buyer"].casefold() in blocked
    ]


def render_text(template, username, order_ids):
    numbers = ", ".join(f"#{order_id}" for order_id in order_ids)
    return template.replace(REVIEW_REMINDER_USERNAME_VARIABLE, str(username)).replace(
        REVIEW_REMINDER_ORDER_VARIABLE, numbers
    )


def has_review(order):
    review = getattr(order, "review", None)
    return review is not None and bool(review.stars or review.text)


class ReviewReminder:
    def __init__(self, cardinal, store=None, clock=time.time, sleep=time.sleep):
        self.cardinal = cardinal
        self.store = store if store is not None else ReviewReminderStore()
        self.clock = clock
        self.sleep = sleep
        self.next_check = clock() + REVIEW_REMINDER_FIRST_CHECK_SECONDS

    def start(self):
        Thread(target=self.loop, name=REVIEW_REMINDER_THREAD_NAME, daemon=True).start()
        return self

    def loop(self):
        while True:
            self.sleep(REVIEW_REMINDER_TICK_SECONDS)
            try:
                self.tick()
            except Exception:
                logger.debug("TRACEBACK", exc_info=True)

    def tick(self):
        now = self.clock()
        if now >= self.next_check:
            self.next_check = now + REVIEW_REMINDER_CHECK_SECONDS
            self.store.prune(now)
            try:
                self.check(now)
            except Exception:
                logger.warning("Не удалось проверить заказы для напоминаний об отзыве.")
                logger.debug("TRACEBACK", exc_info=True)
        if self.store.dirty:
            self.store.save()

    def confirmed(self, order):
        if not self.store.enabled or order.status is not OrderStatuses.CLOSED:
            return False
        name = str(order.buyer_username or "").strip()
        if not name or not order.id:
            return False
        return self.store.add(
            order.id, name, order.buyer_id, order.chat_id, self.clock()
        )

    def observe(self, message):
        if not self.store.enabled or getattr(message, "i_am_seller", None) is False:
            return
        kind = getattr(message, "type", None) or getattr(
            message, "last_message_type", None
        )
        if kind in REVIEW_TYPES:
            status = REVIEW_STATUS_REVIEWED
        elif kind is MessageTypes.ORDER_CONFIRMED_BY_ADMIN:
            status = REVIEW_STATUS_SKIPPED
        else:
            return
        found = RegularExpressions().ORDER_ID.findall(str(message))
        order_ids = [number[1:] for number in found]
        if order_ids:
            self.store.finish(order_ids, status, self.clock())

    def template(self):
        return self.store.text or Localizer().translate("rv_default_text")

    def check(self, now):
        account = self.cardinal.account
        if not self.store.enabled or not account.is_initiated:
            return 0
        if getattr(self.cardinal, "_process_stopping", False):
            return 0
        blacklist = getattr(self.cardinal, "blacklist", ())
        pending = dict(self.store.pending)
        blocked = blocked_orders(pending, blacklist)
        if blocked:
            self.store.finish(blocked, REVIEW_STATUS_SKIPPED, now)
        groups = due_reviews(pending, now, self.store.hours, blacklist)
        selected, wanted = [], []
        for name, order_ids in groups.items():
            room = REVIEW_REMINDER_ORDER_LIMIT - len(wanted)
            if len(selected) >= REVIEW_REMINDER_BATCH_LIMIT or room <= 0:
                break
            selected.append((name, order_ids[:room]))
            wanted.extend(order_ids[:room])
        if not wanted:
            return 0
        orders = account.get_orders_by_ids(*wanted)
        sent = 0
        attempted = False
        for name, order_ids in selected:
            ready = self.sort(account, orders, order_ids, now)
            if not ready:
                continue
            if attempted:
                self.sleep(REVIEW_REMINDER_SEND_PAUSE)
            attempted = True
            sent += self.send(ready)
        return sent

    def sort(self, account, orders, order_ids, now):
        ready, reviewed, skipped = [], [], []
        for order_id in order_ids:
            order = orders.get(order_id)
            if order is None:
                continue
            if (
                order.status is not OrderStatuses.CLOSED
                or order.seller_id != account.id
            ):
                skipped.append(order_id)
            elif has_review(order):
                reviewed.append(order_id)
            else:
                ready.append(order)
        if reviewed:
            self.store.finish(reviewed, REVIEW_STATUS_REVIEWED, now)
        if skipped:
            self.store.finish(skipped, REVIEW_STATUS_SKIPPED, now)
        return ready

    def send(self, orders):
        first = orders[0]
        entry = self.store.pending.get(str(first.id), {})
        username = first.buyer_username or entry.get("buyer")
        chat_id = first.chat_id or entry.get("chat_id")
        buyer_id = first.buyer_id or entry.get("buyer_id")
        order_ids = [order.id for order in orders]
        text = render_text(self.template(), username, order_ids)
        result = self.cardinal.send_message(chat_id, text, username, buyer_id)
        ok = bool(result) and not isinstance(result, MessageSendFailure)
        status = REVIEW_STATUS_SENT if ok else REVIEW_STATUS_FAILED
        self.store.finish(order_ids, status, self.clock())
        numbers = ", ".join(f"#{order_id}" for order_id in order_ids)
        if not ok:
            logger.warning(
                "Не удалось напомнить %s об отзыве на заказ %s.", username, numbers
            )
            return 0
        logger.info("Напомнил %s оставить отзыв на заказ %s.", username, numbers)
        return 1
