import logging
import time
from html import escape
from queue import Empty, Queue
from threading import RLock, Thread

from telebot.apihelper import ApiTelegramException

from tg_bot import utils
from tg_bot.chat_sync.binding import ChatSyncBinding
from tg_bot.chat_sync.media import UnsupportedMedia, download_media
from tg_bot.chat_sync.render import (
    header_keyboard,
    header_text,
    photo_fallback,
    render_parts,
    split_text,
    stack_icon,
    topic_title,
    translate,
)
from tg_bot.chat_sync.helpers import ChatSyncHelpers
from tg_bot.chat_sync.pool import SenderPool
from tg_bot.chat_sync.sender import (
    EchoFilter,
    retry_after,
    thread_closed,
    thread_missing,
)
from tg_bot.chat_sync.store import ChatSyncStore
from tg_bot.constants.chat_sync import CHAT_SYNC_BATCH_SECONDS, CHAT_SYNC_ICONS
from tg_bot.message_formatting import message_is_ad
from Utils.cardinal_tools import safe_text

logger = logging.getLogger("CoxerHubBot.chat_sync")


class ChatSyncService(ChatSyncBinding, ChatSyncHelpers):
    def __init__(self, cardinal, bot, store=None, pool=None, echo=None, start=True):
        self.cardinal = cardinal
        self.bot = bot
        self.store = store or ChatSyncStore()
        self.pool = pool or SenderPool(bot)
        self.echo = echo or EchoFilter()
        self.topic_lock = RLock()
        self.inbox = Queue()
        self.outbox = Queue()
        self.last_stack = None
        self.icon_ids = None
        self.syncing = False
        self.startup_synced = False
        self.load_helpers()
        if start:
            self.start()

    def start(self):
        for target, name in (
            (self.inbox_loop, "cxh-chat-sync-in"),
            (self.outbox_loop, "cxh-chat-sync-out"),
        ):
            Thread(target=target, name=name, daemon=True).start()
        Thread(
            target=self.refresh_helpers, name="cxh-chat-sync-helpers", daemon=True
        ).start()

    @property
    def chat_id(self):
        return self.store.chat_id

    def active(self):
        return self.store.chat_id is not None

    def authorized(self, user):
        telegram = self.cardinal.telegram
        return (
            user is not None
            and not user.is_bot
            and telegram is not None
            and user.id in telegram.authorized_users
        )

    def call(self, method, *args, **kwargs):
        return self.pool.call(method, *args, **kwargs)

    def icon_id(self, key):
        if self.icon_ids is None:
            try:
                stickers = self.bot.get_forum_topic_icon_stickers() or []
                self.icon_ids = {
                    sticker.get("custom_emoji_id")
                    if isinstance(sticker, dict)
                    else getattr(sticker, "custom_emoji_id", None)
                    for sticker in stickers
                }
            except Exception:
                self.icon_ids = set()
                logger.debug("TRACEBACK", exc_info=True)
        value = CHAT_SYNC_ICONS.get(key)
        return value if value in self.icon_ids else None

    def topic(self, fp_chat_id, name, create=True):
        with self.topic_lock:
            thread = self.store.thread_for(fp_chat_id)
            if thread is not None or not create or not self.active():
                return thread
            options = {}
            icon = self.icon_id("new")
            if icon:
                options["icon_custom_emoji_id"] = icon
            topic = self.call(
                "create_forum_topic",
                self.chat_id,
                topic_title(name, fp_chat_id),
                topics=True,
                **options,
            )
            thread = topic.message_thread_id
            self.store.remember(fp_chat_id, name, thread)
            if icon:
                self.store.set_icon(thread, "new")
            logger.info(
                "Чат FunPay %s (%s) связан с темой Telegram %s.",
                name,
                fp_chat_id,
                thread,
            )
        self.post_header(fp_chat_id, name, thread)
        return thread

    def post_header(self, fp_chat_id, name, thread):
        try:
            self.call(
                "send_message",
                self.chat_id,
                header_text(name, fp_chat_id),
                message_thread_id=thread,
                reply_markup=header_keyboard(fp_chat_id),
                disable_notification=True,
                main_only=True,
            )
        except Exception:
            logger.warning(
                "Не удалось отправить карточку чата FunPay %s в тему.", fp_chat_id
            )
            logger.debug("TRACEBACK", exc_info=True)

    def deliver(self, fp_chat_id, name, send):
        thread = self.topic(fp_chat_id, name)
        for attempt in range(2):
            if thread is None:
                return False
            try:
                send(thread)
                return True
            except ApiTelegramException as error:
                if attempt or not (thread_missing(error) or thread_closed(error)):
                    raise
                if thread_closed(error):
                    self.call("reopen_forum_topic", self.chat_id, thread, topics=True)
                    continue
                self.store.forget(fp_chat_id)
                thread = self.topic(fp_chat_id, name)
        return False

    def accept(self, event):
        if not self.active() or self.cardinal.old_mode_enabled:
            return
        stack = getattr(event, "stack", None)
        stack_id = stack.id() if stack is not None else id(event)
        if stack_id == self.last_stack:
            return
        self.last_stack = stack_id
        events = stack.get_stack() if stack is not None else [event]
        self.inbox.put([item.message for item in events])

    def accept_initial(self, event):
        if self.startup_synced or not self.active():
            return
        self.startup_synced = True
        self.start_sync()

    def inbox_loop(self):
        while True:
            messages = self.inbox.get()
            try:
                self.forward(messages)
            except Exception:
                logger.error("Не удалось переслать сообщения FunPay в тему Telegram.")
                logger.debug("TRACEBACK", exc_info=True)

    def visible(self, message):
        own = message.author_id == self.cardinal.account.id
        if own and self.echo.consume(message):
            return False
        if own:
            return self.store.option("bot" if message.by_bot else "own")
        if message_is_ad(message):
            return self.store.option("ads")
        return True

    def forward(self, messages):
        if not messages or not self.active():
            return
        fp_chat_id, name = messages[0].chat_id, messages[0].chat_name
        shown = [message for message in messages if self.visible(message)]
        icon = stack_icon(messages)
        if not shown and not icon:
            return
        own_id = self.cardinal.account.id
        silent = all(message.author_id == own_id for message in shown)
        hide = self.store.option("watermark")
        for part in render_parts(self.cardinal, shown, hide):
            self.deliver(
                fp_chat_id,
                name,
                lambda thread, part=part: self.send_part(thread, part, silent),
            )
        if icon:
            self.update_icon(fp_chat_id, name, icon)

    def send_part(self, thread, part, silent):
        options = {"message_thread_id": thread, "disable_notification": silent}
        if part[0] != "photo":
            return self.call("send_message", self.chat_id, part[1], **options)
        try:
            return self.call(
                "send_photo", self.chat_id, part[1], caption=part[2] or None, **options
            )
        except ApiTelegramException as error:
            if thread_missing(error) or thread_closed(error) or retry_after(error):
                raise
            return self.call(
                "send_message", self.chat_id, photo_fallback(part), **options
            )

    def update_icon(self, fp_chat_id, name, key):
        thread = self.store.thread_for(fp_chat_id)
        icon = self.icon_id(key)
        if thread is None or icon is None or self.store.icon(thread) == key:
            return
        try:
            self.call(
                "edit_forum_topic",
                self.chat_id,
                thread,
                icon_custom_emoji_id=icon,
                topics=True,
            )
            self.store.set_icon(thread, key)
        except ApiTelegramException:
            logger.debug("TRACEBACK", exc_info=True)

    def target(self, message):
        if not self.active() or message.chat.id != self.chat_id:
            return None
        thread = getattr(message, "message_thread_id", None)
        if not thread or not getattr(message, "is_topic_message", False):
            return None
        return self.store.chat_for(thread)

    def outgoing_wanted(self, message):
        if not self.authorized(message.from_user):
            return False
        if message.content_type == "text" and (message.text or "").startswith("/"):
            return False
        return self.target(message) is not None

    def queue_outgoing(self, message):
        self.outbox.put((message.message_id, message))

    def outbox_loop(self):
        while True:
            batch = [self.outbox.get()]
            time.sleep(CHAT_SYNC_BATCH_SECONDS)
            while True:
                try:
                    batch.append(self.outbox.get_nowait())
                except Empty:
                    break
            for item in sorted(batch, key=lambda entry: entry[0]):
                try:
                    self.send_outgoing(item[1])
                except Exception:
                    logger.error(
                        "Не удалось отправить сообщение из темы Telegram в FunPay."
                    )
                    logger.debug("TRACEBACK", exc_info=True)

    def send_text(self, key, name, text):
        self.echo.expect(key, text)
        result = self.cardinal.send_message(
            utils.parse_chat_id(key), text, name, watermark=False
        )
        self.echo.sent(key, getattr(result, "sent_messages", None) or result)
        return bool(result)

    def send_outgoing(self, message):
        target = self.target(message)
        if target is None:
            return
        key, name = target
        if message.content_type == "text":
            text = (message.text or "").strip()
            if text and not self.send_text(key, name, text):
                self.reply(message, translate("cs_send_failed"))
            return
        caption = (message.caption or "").strip()
        if caption and not self.send_text(key, name, caption):
            self.reply(message, translate("cs_send_failed"))
            return
        try:
            data = download_media(self.bot, message)
        except UnsupportedMedia as error:
            self.reply(message, translate(error.key))
            return
        self.send_image(message, key, name, data)

    def send_image(self, message, key, name, data):
        self.echo.expect(key)
        try:
            result = self.cardinal.account.send_image(
                utils.parse_chat_id(key),
                data,
                name,
                add_to_ignore_list=True,
                update_last_saved_message=self.cardinal.old_mode_enabled,
            )
        except Exception as error:
            logger.warning("Не удалось отправить изображение в чат FunPay %s.", key)
            logger.debug("TRACEBACK", exc_info=True)
            reason = getattr(error, "error_message", None)
            text = translate("cs_send_failed")
            self.reply(message, f"{text} {escape(reason)}" if reason else text)
            return
        self.echo.sent(key, [result])

    def reply(self, message, text):
        try:
            self.call(
                "send_message",
                message.chat.id,
                text,
                message_thread_id=message.message_thread_id,
                reply_to_message_id=message.message_id,
            )
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)

    def post(self, thread, text, **options):
        for chunk in split_text(text):
            self.call(
                "send_message", self.chat_id, chunk, message_thread_id=thread, **options
            )

    def send_template(self, key, name, index):
        templates = self.cardinal.telegram.answer_templates
        if not 0 <= index < len(templates):
            return None
        text = templates[index].replace("$username", safe_text(name or ""))
        return text if self.send_text(key, name, text) else False
