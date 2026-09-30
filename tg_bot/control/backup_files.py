import logging
import tempfile
from pathlib import Path

from app.constants.runtime import PROJECT_ROOT
from locales.localizer import Localizer
from Utils.backups.service import BackupService
from Utils.backups.constants import MAX_UPLOAD_BYTES


def send_backup(controller, message):
    if not controller.menu_user_allowed(message.from_user, message.chat):
        return
    translate = Localizer().translate
    try:
        with BackupService(PROJECT_ROOT).snapshot() as snapshot:
            controller.bot.send_document(
                message.chat.id,
                snapshot,
                visible_file_name="backup.zip",
                caption=translate("update_backup"),
            )
    except FileNotFoundError:
        controller.bot.send_message(
            message.chat.id, translate("update_backup_not_found")
        )
    except Exception:
        logging.getLogger("TGBot").exception("Could not send backup")
        controller.bot.send_message(
            message.chat.id, translate("update_backup_send_error")
        )


def restore_upload(controller, message):
    if not controller.menu_user_allowed(message.from_user, message.chat):
        return
    document = message.document
    if not document or not (document.file_name or "").lower().endswith(".zip"):
        controller.bot.send_message(
            message.chat.id, "Отправьте резервную копию в формате ZIP."
        )
        return
    if not document.file_size or document.file_size > MAX_UPLOAD_BYTES:
        controller.bot.send_message(
            message.chat.id, "Архив должен быть не больше 20 МБ."
        )
        return
    try:
        file = controller.bot.get_file(document.file_id)
        data = controller.bot.download_file(file.file_path)
        restore_downloaded(data)
    except Exception:
        logging.getLogger("TGBot").exception(
            "Backup restore failed; details in log.log"
        )
        controller.bot.send_message(
            message.chat.id, "Не удалось восстановить копию. Подробности — в log.log."
        )
        return
    controller.bot.send_message(
        message.chat.id,
        "Копия восстановлена. Перезапустите бот кнопкой в разделе «Инструменты».",
    )


def restore_downloaded(data):
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded archive exceeds the size limit")
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "backup.zip"
        archive.write_bytes(data)
        BackupService(PROJECT_ROOT).restore(archive)
