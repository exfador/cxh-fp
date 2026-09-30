import hashlib
import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests
from telebot import apihelper

from app.constants.branding import PROJECT_NAME
from app.constants.runtime import PROJECT_ROOT
from tg_bot.constants import profile as settings
from tg_bot.profile_assets import read_profile_text


class BotProfileBranding:
    def __init__(self, token, root=PROJECT_ROOT, request=apihelper._make_request):
        self.token = token
        self.root = Path(root)
        self.request = request
        self.logger = logging.getLogger("CoxerHubBot.telegram.profile")

    def call(self, method, parameters=None, files=None):
        payload = dict(parameters or {})
        payload["timeout"] = settings.PROFILE_TIMEOUT_SECONDS
        return self.request(
            self.token, method, method="post", params=payload, files=files
        )

    def synchronize(self):
        results = {}
        for section, action in (("text", self.sync_text), ("avatar", self.sync_avatar)):
            try:
                action()
                results[section] = True
            except (
                apihelper.ApiException,
                requests.RequestException,
                OSError,
                ValueError,
                TypeError,
                KeyError,
                IndexError,
            ):
                results[section] = False
                self.logger.warning("Не удалось обновить оформление бота: %s", section)
        return results

    def expected_text(self, language, field):
        if language == "uk":
            return ""
        if field == "name":
            return PROJECT_NAME
        fallback = settings.PROFILE_SHORT_DESCRIPTION
        if language == "en":
            fallback = settings.PROFILE_SHORT_DESCRIPTION_EN
        if field == "description":
            fallback = settings.PROFILE_DESCRIPTIONS[language]
        return read_profile_text(self.root, language, field, fallback)

    def sync_text(self):
        desired_texts = {
            (language, field): self.expected_text(language, field)
            for language in settings.PROFILE_LANGUAGES
            for _, field in settings.PROFILE_FIELDS
        }
        for language in settings.PROFILE_LANGUAGES:
            for suffix, field in settings.PROFILE_FIELDS:
                desired = desired_texts[language, field]
                parameters = {"language_code": language}
                current = self.call(f"getMy{suffix}", parameters)[field]
                if current != desired:
                    self.call(f"setMy{suffix}", {**parameters, field: desired})

    def photo_identity(self, bot_id):
        response = self.call("getUserProfilePhotos", {"user_id": bot_id, "limit": 1})
        photos = response["photos"]
        return photos[0][-1]["file_unique_id"] if photos else None

    def sync_avatar(self):
        avatar = self.root / settings.PROFILE_AVATAR_PATH
        digest = hashlib.sha256(avatar.read_bytes()).hexdigest()
        bot_id = self.call("getMe")["id"]
        photo_id = self.photo_identity(bot_id)
        state = {"bot_id": bot_id, "sha256": digest, "photo_id": photo_id}
        if photo_id and self.read_cache() == state:
            return
        self.upload_avatar(avatar)
        state["photo_id"] = self.photo_identity(bot_id)
        if not state["photo_id"]:
            raise ValueError("Missing profile photo after upload")
        self.write_cache(state)

    def upload_avatar(self, avatar):
        attachment = settings.PROFILE_PHOTO_ATTACHMENT
        payload = {
            "type": settings.PROFILE_PHOTO_TYPE,
            "photo": f"attach://{attachment}",
        }
        with avatar.open("rb") as stream:
            files = {
                attachment: (
                    settings.PROFILE_PHOTO_FILENAME,
                    stream,
                    settings.PROFILE_PHOTO_MIME,
                )
            }
            self.call(
                settings.PROFILE_PHOTO_METHOD, {"photo": json.dumps(payload)}, files
            )

    def read_cache(self):
        destination = self.root / settings.PROFILE_CACHE_PATH
        try:
            if destination.stat().st_size > settings.PROFILE_CACHE_LIMIT_BYTES:
                raise ValueError("Oversized profile state")
            return json.loads(destination.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            self.logger.debug("Состояние оформления бота недоступно; проверяем заново")
            return None

    def write_cache(self, state):
        destination = self.root / settings.PROFILE_CACHE_PATH
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=destination.parent, delete=False
            ) as stream:
                temporary_path = Path(stream.name)
                os.chmod(temporary_path, settings.PROFILE_CACHE_MODE)
                json.dump(state, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, destination)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
