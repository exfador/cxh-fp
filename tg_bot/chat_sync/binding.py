import logging
from html import escape
from threading import Thread

from tg_bot import utils
from tg_bot.chat_sync.render import format_block, templates_keyboard, translate
from tg_bot.constants.chat_sync import (
    CHAT_SYNC_ADMIN_STATUSES,
    CHAT_SYNC_BIND_COMMAND,
    CHAT_SYNC_GONE_STATUSES,
    CHAT_SYNC_HISTORY_LIMIT,
    CHAT_SYNC_SUPERGROUP,
    CHAT_SYNC_SYNC_LIMIT,
)

logger = logging.getLogger("CoxerHubBot.chat_sync")


class ChatSyncBinding:
    def inspect(self, chat_id):
        problems = []
        try:
            chat = self.bot.get_chat(chat_id)
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            return {"title": None, "problems": ["cs_problem_unreachable"]}
        if not getattr(chat, "is_forum", False):
            problems.append("cs_problem_topics")
        try:
            member = self.bot.get_chat_member(chat_id, self.bot.user.id)
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            problems.append("cs_problem_unreachable")
        else:
            if member.status not in CHAT_SYNC_ADMIN_STATUSES:
                problems.append("cs_problem_admin")
            elif member.status != "creator" and not getattr(
                member, "can_manage_topics", False
            ):
                problems.append("cs_problem_topics_right")
        return {"title": getattr(chat, "title", None), "problems": problems}

    def problems_text(self, problems):
        return "\n".join(f"• {translate(problem)}" for problem in problems)

    def post_general(self, chat_id, text):
        try:
            self.call("send_message", chat_id, text, main_only=True)
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)

    def bind_group(self, chat, force=False):
        report = self.inspect(chat.id)
        if report["problems"]:
            text = self.problems_text(report["problems"])
            self.post_general(
                chat.id, translate("cs_bind_problems", text, CHAT_SYNC_BIND_COMMAND)
            )
            return False
        title = report["title"] or getattr(chat, "title", "") or ""
        if self.chat_id == chat.id:
            self.store.rename(title)
            self.post_general(chat.id, translate("cs_already_bound"))
            return True
        if self.chat_id is not None and not force:
            self.post_general(
                chat.id, translate("cs_other_bound", CHAT_SYNC_BIND_COMMAND)
            )
            return False
        self.store.bind(chat.id, title)
        self.startup_synced = True
        logger.info(
            "Группа Telegram %s (%s) привязана к синхронизации чатов.", title, chat.id
        )
        self.post_general(chat.id, translate("cs_bound"))
        self.start_sync()
        return True

    def unbind(self):
        chat_id = self.chat_id
        self.store.unbind()
        logger.info("Группа Telegram %s отвязана от синхронизации чатов.", chat_id)

    def membership(self, update):
        chat, status = update.chat, update.new_chat_member.status
        if chat.id == self.chat_id and status in CHAT_SYNC_GONE_STATUSES:
            logger.warning("Бота удалили из группы синхронизации чатов %s.", chat.id)
            return
        if not self.authorized(update.from_user) or status in CHAT_SYNC_GONE_STATUSES:
            return
        if chat.type != CHAT_SYNC_SUPERGROUP:
            self.post_general(
                chat.id, translate("cs_need_topics", CHAT_SYNC_BIND_COMMAND)
            )
            return
        if status not in CHAT_SYNC_ADMIN_STATUSES:
            self.post_general(chat.id, translate("cs_need_admin"))
            return
        self.bind_group(chat)

    def bind_command(self, message):
        if self.authorized(message.from_user) and message.chat.type != "private":
            self.bind_group(message.chat, force=True)

    def status(self):
        if not self.active():
            return None
        report = self.inspect(self.chat_id)
        if report["title"]:
            self.store.rename(report["title"])
        if self.cardinal.old_mode_enabled:
            report["problems"].append("cs_problem_old_mode")
        return report

    def start_sync(self):
        if self.syncing or not self.active():
            return False
        self.syncing = True
        Thread(
            target=self.sync_recent, name="cxh-chat-sync-topics", daemon=True
        ).start()
        return True

    def sync_recent(self):
        created = 0
        try:
            chats = self.cardinal.account.get_chats(update=True)
            ordered = sorted(
                chats.values(), key=lambda chat: chat.node_msg_id or 0, reverse=True
            )
            for chat in ordered[:CHAT_SYNC_SYNC_LIMIT]:
                if not self.active():
                    break
                if self.store.thread_for(chat.id) is None:
                    created += self.topic(chat.id, chat.name) is not None
        except Exception:
            logger.warning("Не удалось создать темы для последних чатов FunPay.")
            logger.debug("TRACEBACK", exc_info=True)
        finally:
            self.syncing = False
        if created:
            logger.info("Создано тем для чатов FunPay: %s.", created)
        return created

    def history_command(self, message):
        if not self.authorized(message.from_user):
            return
        target = self.target(message)
        if target is not None:
            self.history(target[0], target[1], message.message_thread_id)

    def history(self, key, name, thread):
        try:
            messages = self.cardinal.account.get_chat_history(
                utils.parse_chat_id(key), interlocutor_username=name
            )
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            self.post(thread, translate("cs_history_failed"))
            return
        messages = list(messages or [])[-CHAT_SYNC_HISTORY_LIMIT:]
        if not messages:
            self.post(thread, translate("cs_history_empty"))
            return
        text = format_block(self.cardinal, messages, self.store.option("watermark"))
        self.post(thread, text, disable_notification=True)

    def callback(self, call):
        parts = (call.data or "").split(":")
        message = call.message
        if (
            len(parts) < 3
            or message is None
            or message.chat.id != self.chat_id
            or not self.authorized(call.from_user)
        ):
            self.bot.answer_callback_query(call.id)
            return
        action, key = parts[1], parts[2]
        thread = self.store.thread_for(key)
        name = self.store.names.get(key)
        if thread is None:
            self.bot.answer_callback_query(call.id, translate("cs_topic_unknown"))
            return
        if action == "h":
            self.bot.answer_callback_query(call.id, translate("cs_history_loading"))
            Thread(target=self.history, args=(key, name, thread), daemon=True).start()
        elif action == "t":
            self.open_templates(call, key, thread)
        elif action == "s" and len(parts) > 3 and parts[3].isdigit():
            self.template_clicked(call, key, name, thread, int(parts[3]))
        elif action == "x":
            self.bot.answer_callback_query(call.id)
            self.bot.delete_message(message.chat.id, message.message_id)
        else:
            self.bot.answer_callback_query(call.id)

    def open_templates(self, call, key, thread):
        templates = self.cardinal.telegram.answer_templates
        if not templates:
            self.bot.answer_callback_query(
                call.id, translate("cs_no_templates"), show_alert=True
            )
            return
        self.bot.answer_callback_query(call.id)
        self.call(
            "send_message",
            self.chat_id,
            translate("cs_templates_title"),
            message_thread_id=thread,
            reply_markup=templates_keyboard(key, templates),
            disable_notification=True,
            main_only=True,
        )

    def template_clicked(self, call, key, name, thread, index):
        text = self.send_template(key, name, index)
        if text is None:
            self.bot.answer_callback_query(call.id, translate("cs_topic_unknown"))
            return
        self.bot.answer_callback_query(
            call.id, translate("cs_sent_short" if text else "cs_failed_short")
        )
        if text:
            self.post(
                thread,
                translate("cs_template_sent", escape(text)),
                disable_notification=True,
            )
