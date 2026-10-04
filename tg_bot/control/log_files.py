import logging

from app.constants.runtime import PROJECT_ROOT
from locales.localizer import Localizer
from Utils.logger import flush_logs
from Utils.logging_support.files import snapshot_logs, clear_log_archives
from Utils.logging_support.runtime import current_runtime


def send_logs(controller, message):
    if not controller.menu_user_allowed(message.from_user, message.chat):
        return
    translate = Localizer().translate
    try:
        flush_logs()
        runtime = current_runtime()
        lock = runtime.file.lock if runtime else None
        with snapshot_logs(PROJECT_ROOT, lock) as snapshot:
            controller.bot.send_document(
                message.chat.id, snapshot, visible_file_name="log.log"
            )
    except FileNotFoundError:
        controller.bot.send_message(message.chat.id, translate("logfile_not_found"))
    except Exception:
        logging.getLogger("TGBot").error("Could not export logs; details in log.log")
        logging.getLogger("TGBot").debug("TRACEBACK", exc_info=True)
        controller.bot.send_message(message.chat.id, translate("logfile_error"))


def clear_logs_text():
    translate = Localizer().translate
    runtime = current_runtime()
    try:
        flush_logs()
        if runtime is not None:
            runtime.file.acquire()
        try:
            deleted = clear_log_archives(PROJECT_ROOT)
        finally:
            if runtime is not None:
                runtime.file.release()
        return translate("logfile_deleted").format(deleted)
    except (OSError, ValueError):
        logging.getLogger("TGBot").exception("Could not clear archived logs")
        return translate("logfile_error")


def clear_logs(controller, message):
    controller.bot.send_message(message.chat.id, clear_logs_text())
