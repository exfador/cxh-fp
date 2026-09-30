import logging
import zipfile
from pathlib import Path
from Utils.backups.service import BackupService

logger = logging.getLogger("FunPay CoxerHub.backups")


def create_backup() -> int:
    try:
        BackupService(Path.cwd()).create()
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        logger.error("Backup creation failed: %s", type(error).__name__)
        return 1


def extract_backup_archive() -> bool:
    try:
        BackupService(Path.cwd()).extract()
        return True
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        logger.error("Backup extraction failed: %s", type(error).__name__)
        return False


def install_backup() -> bool:
    try:
        BackupService(Path.cwd()).install()
        return True
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        logger.error("Backup installation failed: %s", type(error).__name__)
        return False
