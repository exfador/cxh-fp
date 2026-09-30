import json
import logging
from pathlib import Path
from threading import Lock
from time import monotonic

import requests
from telebot import apihelper

from app.constants.runtime import PROJECT_ROOT
from tg_bot.constants import premium_emoji as settings


def load_owner_id(token, root):
    path = Path(root) / settings.OWNER_SETTINGS_PATH
    try:
        if path.stat().st_size > settings.OWNER_SETTINGS_LIMIT_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"bot_id", "owner_id"}:
            return None
        if type(data["owner_id"]) is not int or data["owner_id"] <= 0:
            return None
        return (
            data["owner_id"] if data["bot_id"] == int(token.split(":", 1)[0]) else None
        )
    except (OSError, ValueError, TypeError):
        return None


class OwnerPremiumPolicy:
    def __init__(
        self, token, root=PROJECT_ROOT, request=apihelper._make_request, clock=monotonic
    ):
        self.token = token
        self.owner_id = load_owner_id(token, root)
        self.request = request
        self.clock = clock
        self.lock = Lock()
        self.premium = False
        self.expires_at = 0
        self.logger = logging.getLogger("CoxerHubBot.telegram.premium")

    def enabled(self):
        if self.owner_id is None:
            return False
        with self.lock:
            if self.clock() >= self.expires_at:
                self.refresh()
            return self.premium

    def refresh(self):
        self.premium = False
        self.expires_at = self.clock() + settings.PREMIUM_RETRY_SECONDS
        try:
            response = self.request(
                self.token,
                "getChatMember",
                params={
                    "chat_id": self.owner_id,
                    "user_id": self.owner_id,
                    "timeout": settings.PREMIUM_NETWORK_TIMEOUT,
                },
            )
            user = response["user"]
            self.premium = (
                user["id"] == self.owner_id and user.get("is_premium") is True
            )
            self.expires_at = self.clock() + settings.PREMIUM_REFRESH_SECONDS
        except (
            apihelper.ApiException,
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
        ):
            self.logger.debug("Premium владельца не подтверждён; обычные эмодзи")

    def observe(self, user):
        if user is None or user.id != self.owner_id:
            return
        with self.lock:
            self.premium = getattr(user, "is_premium", False) is True
            self.expires_at = self.clock() + settings.PREMIUM_REFRESH_SECONDS

    def disable(self):
        with self.lock:
            self.premium = False
            self.expires_at = self.clock() + settings.PREMIUM_RETRY_SECONDS
