import logging
import re
from threading import Thread

import telebot
from telebot.apihelper import ApiTelegramException

from locales.localizer import Localizer
from tg_bot.chat_sync.pool import Lane
from tg_bot.constants.chat_sync import (
    CHAT_SYNC_ADMIN_STATUSES,
    CHAT_SYNC_GONE_STATUSES,
    CHAT_SYNC_HELPER_LANGUAGES,
    CHAT_SYNC_HELPER_LIMIT,
    CHAT_SYNC_TOKEN_PATTERN,
)
from tg_bot.constants.profile import PROFILE_AVATAR_PATH
from app.constants.branding import PROJECT_NAME

logger = logging.getLogger("CoxerHubBot.chat_sync")


def brand_helper(token):
    from tg_bot.profile_branding import BotProfileBranding

    branding = BotProfileBranding(token)
    try:
        for language in CHAT_SYNC_HELPER_LANGUAGES:
            parameters = {"language_code": language}
            branding.call("setMyName", {**parameters, "name": PROJECT_NAME})
            text = Localizer().translate(
                "cs_helper_description", language=language or "ru"
            )
            branding.call("setMyDescription", {**parameters, "description": text})
            branding.call(
                "setMyShortDescription", {**parameters, "short_description": text}
            )
        bot_id = branding.call("getMe")["id"]
        if not branding.photo_identity(bot_id):
            branding.upload_avatar(branding.root / PROFILE_AVATAR_PATH)
    except Exception:
        logger.warning("Не удалось оформить бота-помощника синхронизации чатов.")
        logger.debug("TRACEBACK", exc_info=True)


class ChatSyncHelpers:
    def helper_bot(self, token):
        return telebot.TeleBot(token, parse_mode="HTML", threaded=False)

    def load_helpers(self):
        lanes = [
            Lane(self.helper_bot(entry["token"]), False, entry["id"], entry["username"])
            for entry in self.store.helper_entries()
        ]
        self.pool.set_helpers(lanes)

    def main_bot_id(self):
        try:
            return self.bot.user.id
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            return None

    def add_helper(self, token):
        token = (token or "").strip()
        entries = self.store.helper_entries()
        if not re.fullmatch(CHAT_SYNC_TOKEN_PATTERN, token):
            return "cs_helper_bad_token", None
        if token == self.bot.token:
            return "cs_helper_is_main", None
        if any(entry["token"] == token for entry in entries):
            return "cs_helper_exists", None
        if len(entries) >= CHAT_SYNC_HELPER_LIMIT:
            return "cs_helper_limit", None
        try:
            me = self.helper_bot(token).get_me()
        except ApiTelegramException as error:
            if error.error_code in (401, 404):
                return "cs_helper_bad_token", None
            return "cs_helper_check_failed", None
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            return "cs_helper_check_failed", None
        if not me.is_bot or me.id == self.main_bot_id():
            return "cs_helper_is_main", None
        if any(entry["id"] == me.id for entry in entries):
            return "cs_helper_exists", None
        self.store.add_helper(token, me.id, me.username)
        self.load_helpers()
        Thread(target=brand_helper, args=(token,), daemon=True).start()
        logger.info("Добавлен бот-помощник синхронизации чатов @%s.", me.username)
        return None, me.username

    def remove_helper(self, user_id):
        entry = self.store.remove_helper(user_id)
        if entry is None:
            return None
        self.load_helpers()
        if self.active():
            try:
                self.helper_bot(entry["token"]).leave_chat(self.chat_id)
            except Exception:
                logger.debug("TRACEBACK", exc_info=True)
        logger.info(
            "Бот-помощник @%s удалён из синхронизации чатов.", entry["username"]
        )
        return entry["username"]

    def helper_status(self, lane):
        try:
            lane.bot.get_me()
        except ApiTelegramException as error:
            if error.error_code == 401:
                lane.reason = "token"
                return "token"
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
        if not self.active():
            return "unbound"
        try:
            member = self.bot.get_chat_member(self.chat_id, lane.user_id)
        except Exception:
            logger.debug("TRACEBACK", exc_info=True)
            lane.reason = "group"
            return "missing"
        if member.status in CHAT_SYNC_GONE_STATUSES:
            lane.reason = "group"
            return "missing"
        lane.reason, lane.retry_at = None, 0.0
        lane.topics = member.status == "creator" or (
            member.status in CHAT_SYNC_ADMIN_STATUSES
            and bool(getattr(member, "can_manage_topics", False))
        )
        return "ok" if lane.topics else "send"

    def refresh_helpers(self):
        return [(lane, self.helper_status(lane)) for lane in list(self.pool.helpers)]
