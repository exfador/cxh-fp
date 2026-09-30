import getpass
import os
import sys
from pathlib import Path
from app.constants.branding import SERVICE_PID_FILENAME
from app.constants.filesystem import PRIVATE_PROCESS_MASK
from app.private_storage import secure_existing_storage
import colorama
from Utils.logger import configure_logging
from Utils.single_instance_guard import SingleInstanceGuard
from app.constants.runtime import (
    PROJECT_ROOT,
    DIRECTORIES,
    RESPONSE_CONFIG,
    DELIVERY_CONFIG,
    SERVICE_FLAG,
    SERVICE_PID_DIRECTORY,
)


def prepare_environment() -> None:
    root = (
        PROJECT_ROOT
        if not getattr(sys, "frozen", False)
        else Path(sys.executable).parent
    )
    os.chdir(root)
    os.umask(PRIVATE_PROCESS_MASK)
    SingleInstanceGuard.acquire(root / "run" / "cardinal.lock")
    for directory in DIRECTORIES:
        (root / directory).mkdir(parents=True, exist_ok=True)
    secure_existing_storage(root)
    for filename in (RESPONSE_CONFIG, DELIVERY_CONFIG):
        if not (root / filename).exists():
            (root / filename).touch(exist_ok=False)
    colorama.init()
    configure_logging()
    write_service_pid()


def write_service_pid() -> None:
    if sys.platform != "linux" or os.getenv(SERVICE_FLAG) != "1":
        return
    directory = SERVICE_PID_DIRECTORY / getpass.getuser()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / SERVICE_PID_FILENAME).write_text(str(os.getpid()))
