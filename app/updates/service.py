import logging
import os
import secrets
import sys
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic

from app.constants.runtime import VERSION
from app.constants import update_runtime as settings
from app.updates.dependencies import verify_runtime_dependencies
from app.updates.releases import latest_release
from app.updates.store import load_state, write_state
from app.updates.transport import download_release_archive
from app.updates.manifest import verify_envelope
from app.updates import constants as update_settings


class UpdateService:
    def __init__(self, panel, root, repository, public_key):
        self.panel = panel
        self.root = Path(root)
        self.repository = repository
        self.public_key = public_key
        self.lock = Lock()
        self.stop_event = Event()
        self.pending = None
        self.token = None
        self.checked_at = None
        self.logger = logging.getLogger(settings.UPDATE_LOGGER)

    def start(self):
        if not self.public_key:
            return
        Thread(target=self.poll, name=settings.UPDATE_THREAD_NAME, daemon=True).start()

    def poll(self):
        if self.stop_event.wait(settings.UPDATE_INITIAL_SECONDS):
            return
        while not self.stop_event.is_set():
            try:
                self.notify_result()
            except Exception as error:
                self.logger.warning(
                    "Update result delivery failed: %s", type(error).__name__
                )
            try:
                self.check()
                self.notify()
            except Exception as error:
                self.logger.warning(
                    "Не удалось проверить обновления: %s: %s",
                    type(error).__name__,
                    error,
                )
                self.logger.debug("Release check traceback", exc_info=True)
            self.stop_event.wait(settings.UPDATE_POLL_SECONDS)

    def check(self):
        if not self.public_key:
            return None
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError("Update operation already running")
        try:
            return self.check_locked()
        finally:
            self.lock.release()

    def check_locked(self):
        now = monotonic()
        if (
            self.checked_at is not None
            and now - self.checked_at < settings.UPDATE_CHECK_COOLDOWN
        ):
            return self.pending
        result = latest_release(self.repository, self.public_key, VERSION)
        self.pending = result
        self.token = secrets.token_hex(settings.UPDATE_TOKEN_BYTES) if result else None
        self.checked_at = now
        return result

    def notify(self):
        if not self.lock.acquire(blocking=False):
            return
        try:
            self.notify_locked()
        finally:
            self.lock.release()

    def notify_locked(self):
        if self.pending is None:
            return
        path = self.root / settings.UPDATE_STATE_PATH
        state = load_state(path)
        version = self.pending[0]["version"]
        stored = state.get(version, [])
        recipients = stored if isinstance(stored, list) else []
        for user_id in tuple(self.panel.authorized_users):
            if str(
                user_id
            ) in recipients or not self.panel.notification_recipient_allowed(user_id):
                continue
            if (
                self.panel.update_release_notification(user_id, version, self.token)
                is False
            ):
                continue
            recipients.append(str(user_id))
            state = {version: recipients}
            write_state(path, state)

    def install(self, call, token):
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError("Update operation already running")
        try:
            self.install_locked(call, token)
        finally:
            self.lock.release()

    def install_locked(self, call, token):
        if (
            not isinstance(token, str)
            or not token.isascii()
            or self.pending is None
            or self.token is None
            or not secrets.compare_digest(token, self.token)
        ):
            raise PermissionError("Expired update confirmation")
        self.require_authorized_call(call)
        self.require_managed_runtime()
        manifest, url, envelope = self.pending
        verify_runtime_dependencies(self.root, manifest["files"])
        self.panel.update_progress(call, "progress")
        target = self.root / "storage" / "updates" / "download.zip"
        download_release_archive(url, target, manifest)
        self.require_authorized_call(call)
        self.persist_request(call, envelope)
        self.panel.update_progress(call, "restart")
        self.restart_worker()

    def require_managed_runtime(self):
        supervised = (
            os.getenv(settings.UPDATE_CHILD_FLAG) == settings.UPDATE_CHILD_VALUE
        )
        unsupported = (
            getattr(sys, "frozen", False)
            or Path(update_settings.DOCKER_RUNTIME_MARKER).exists()
        )
        if not supervised or unsupported:
            raise ValueError(update_settings.MANAGED_RUNTIME_ERROR)

    def require_authorized_call(self, call):
        message = getattr(call, "message", None)
        if message is None or not self.panel.menu_user_allowed(
            call.from_user, message.chat
        ):
            raise PermissionError("Update recipient is not authorized")

    def persist_request(self, call, envelope):
        write_state(
            self.root / settings.UPDATE_REQUEST_PATH,
            {
                "envelope": envelope,
                "recipient": call.from_user.id,
                "message_id": call.message.id,
                "previous_version": VERSION,
            },
        )

    def restart_worker(self):
        from Utils.logger import stop_logging

        self.require_managed_runtime()
        self.token = None
        self.stop_event.set()
        stop_logging()
        os._exit(settings.UPDATE_EXIT_CODE)

    def notify_result(self):
        if not self.lock.acquire(blocking=False):
            return
        try:
            path = self.root / settings.UPDATE_REQUEST_PATH
            request = load_state(path)
            if not self.result_recipient_allowed(request):
                return
            if self.panel.update_result_notification(request) is not False:
                write_state(path, {})
        finally:
            self.lock.release()

    def result_recipient_allowed(self, request):
        if (
            type(request) is not dict
            or set(request) != update_settings.UPDATE_RESULT_FIELDS
        ):
            return False
        if (
            not isinstance(request["status"], str)
            or request["status"] not in update_settings.UPDATE_RESULT_STATUSES
            or request["version"] != VERSION
        ):
            return False
        if not self.result_address_allowed(request):
            return False
        manifest = verify_envelope(
            request["envelope"],
            self.public_key,
            self.repository,
            request["previous_version"],
        )
        expected = (
            manifest["version"]
            if request["status"] == "done"
            else request["previous_version"]
        )
        return expected == VERSION

    def result_address_allowed(self, request):
        recipient, message_id = request["recipient"], request["message_id"]
        return (
            type(recipient) is int
            and recipient > 0
            and type(message_id) is int
            and message_id > 0
            and self.panel.notification_recipient_allowed(recipient)
        )
