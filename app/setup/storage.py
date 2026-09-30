import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.constants.setup import CONFIG_FILE_MODE


def write_setup_config(config, filename, replace=False):
    destination = Path(filename)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, delete=False
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            os.chmod(temporary_path, CONFIG_FILE_MODE)
            config.write(temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        if replace:
            os.replace(temporary_path, destination)
        else:
            publish_new_config(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def publish_new_config(temporary_path, destination):
    if os.name == "nt":
        os.rename(temporary_path, destination)
        return
    os.link(temporary_path, destination)
