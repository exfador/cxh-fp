import logging
import time
from threading import Lock

from telebot.apihelper import ApiTelegramException
from telebot.types import LinkPreviewOptions

from tg_bot.chat_sync.sender import error_matches, retry_after
from tg_bot.constants.chat_sync import (
    CHAT_SYNC_HELPER_DOWN,
    CHAT_SYNC_HELPER_RETRY_SECONDS,
    CHAT_SYNC_HELPER_TOPIC_DENIED,
    CHAT_SYNC_RETRY_LIMIT,
    CHAT_SYNC_SEND_INTERVAL,
)

logger = logging.getLogger("CoxerHubBot.chat_sync")


class Lane:
    def __init__(self, bot, main=False, user_id=None, username=None):
        self.bot = bot
        self.main = main
        self.user_id = user_id
        self.username = username
        self.next_slot = 0.0
        self.topics = main
        self.reason = None
        self.retry_at = 0.0

    def usable(self, now):
        return self.main or self.reason is None or now >= self.retry_at


def helper_down(error):
    if not isinstance(error, ApiTelegramException):
        return False
    return error.error_code in (401, 403) or error_matches(error, CHAT_SYNC_HELPER_DOWN)


def topic_denied(error):
    return error_matches(error, CHAT_SYNC_HELPER_TOPIC_DENIED)


class SenderPool:
    def __init__(
        self,
        main_bot,
        interval=CHAT_SYNC_SEND_INTERVAL,
        retries=CHAT_SYNC_RETRY_LIMIT,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        self.interval = interval
        self.retries = retries
        self.sleep = sleep
        self.clock = clock
        self.lock = Lock()
        self.main = Lane(main_bot, main=True)
        self.helpers = []

    @property
    def lanes(self):
        return [self.main, *self.helpers]

    def set_helpers(self, lanes):
        with self.lock:
            known = {lane.user_id: lane for lane in self.helpers}
            for lane in lanes:
                previous = known.get(lane.user_id)
                if previous is not None:
                    lane.next_slot, lane.topics = previous.next_slot, previous.topics
                    lane.reason, lane.retry_at = previous.reason, previous.retry_at
            self.helpers = list(lanes)

    def helper(self, user_id):
        return next((lane for lane in self.helpers if lane.user_id == user_id), None)

    def reserve(self, main_only, topics, skipped):
        now = self.clock()
        with self.lock:
            lanes = [
                lane
                for lane in self.helpers
                if not main_only
                and lane not in skipped
                and lane.usable(now)
                and (lane.topics or not topics)
            ]
            lane = min([self.main, *lanes], key=lambda item: item.next_slot)
            start = max(now, lane.next_slot)
            lane.next_slot = start + self.interval
            return lane, start - now

    def mark_down(self, lane, error):
        with self.lock:
            lane.reason = "token" if error.error_code == 401 else "group"
            lane.retry_at = self.clock() + CHAT_SYNC_HELPER_RETRY_SECONDS

    def mark_ok(self, lane):
        if lane.reason is not None:
            with self.lock:
                lane.reason, lane.retry_at = None, 0.0

    def prepare(self, lane, method, kwargs):
        if not lane.main and method == "send_message":
            kwargs = dict(kwargs)
            kwargs.pop("disable_web_page_preview", None)
            kwargs.setdefault(
                "link_preview_options", LinkPreviewOptions(is_disabled=True)
            )
        return kwargs

    def call(self, method, *args, main_only=False, topics=False, **kwargs):
        skipped = set()
        throttled = 0
        while True:
            lane, wait = self.reserve(main_only, topics, skipped)
            if wait > 0:
                self.sleep(wait)
            try:
                result = getattr(lane.bot, method)(
                    *args, **self.prepare(lane, method, kwargs)
                )
            except ApiTelegramException as error:
                delay = retry_after(error)
                if delay is not None:
                    throttled += 1
                    if throttled > self.retries:
                        raise
                    with self.lock:
                        lane.next_slot = max(lane.next_slot, self.clock() + delay)
                    continue
                if lane.main:
                    raise
                if topics and topic_denied(error):
                    lane.topics = False
                elif helper_down(error):
                    self.mark_down(lane, error)
                else:
                    raise
                skipped.add(lane)
                continue
            self.mark_ok(lane)
            logger.debug(
                "Синхронизация чатов: %s через %s",
                method,
                "основного бота" if lane.main else f"@{lane.username}",
            )
            return result
