import json
import logging
import os
import time
from pathlib import Path

RAISE_SCHEDULE_PATH = Path("storage/cache/raise_schedule.json")
logger = logging.getLogger("FunPay CoxerHub.raise_schedule")


def numeric_map(values, converter):
    result = {}
    if not isinstance(values, dict):
        return result
    for key, value in values.items():
        try:
            result[int(key)] = converter(value)
        except (TypeError, ValueError):
            continue
    return result


def load_raise_schedule(path=RAISE_SCHEDULE_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, {}
    if not isinstance(data, dict):
        return {}, {}
    now = time.time()
    next_times = {
        key: value
        for key, value in numeric_map(data.get("next"), float).items()
        if value > now
    }
    return next_times, numeric_map(data.get("last"), int)


def save_raise_schedule(next_times, last_times, path=RAISE_SCHEDULE_PATH):
    path = Path(path)
    payload = {
        "next": {str(key): value for key, value in next_times.items()},
        "last": {str(key): value for key, value in last_times.items()},
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        logger.debug("Raise schedule was not saved", exc_info=True)
