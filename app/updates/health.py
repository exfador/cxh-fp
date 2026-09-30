import os

from app.constants import update_runtime as settings
from app.constants.runtime import VERSION
from app.updates.store import write_state


def mark_healthy(root):
    nonce = os.getenv(settings.UPDATE_HEALTH_NONCE)
    if nonce is None:
        return
    write_state(
        root / settings.UPDATE_HEALTH_PATH, {"nonce": nonce, "version": VERSION}
    )
