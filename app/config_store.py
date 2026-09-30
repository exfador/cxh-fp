import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.constants.configuration import CONFIG_TEMP_PREFIX


def write_config(config, destination):
    destination = Path(destination)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=CONFIG_TEMP_PREFIX,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            config.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
