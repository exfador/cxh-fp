import json
import logging
import os
import re
import threading
import time
from pathlib import Path

from Utils.single_instance_guard import SingleInstanceGuard

STOP_REQUEST = Path("run/stop.request")
STOP_ACK = Path("run/manual-stop-ack.json")
WORKER_STOP_REQUEST = Path("run/worker-stop.request")
STOP_POLL_SECONDS = 1.0
STOP_WAIT_SECONDS = 60.0
INSTANCE_LOCKS = (Path("run/cardinal.lock"), Path("run/update-supervisor.lock"))
logger = logging.getLogger("main")


def clear_stop_request(root):
    try:
        (Path(root) / STOP_REQUEST).unlink()
    except FileNotFoundError:
        pass


def request_stop(root):
    path = Path(root) / STOP_REQUEST
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps({"time": time.time(), "pid": os.getpid()}))
    os.replace(temporary, path)


def stop_requested(root):
    path = Path(root) / STOP_REQUEST
    if not path.exists():
        return False
    if acknowledge_manual_stop(root):
        clear_stop_request(root)
    return True


def worker_nonce():
    from app.constants import update_runtime as settings

    nonce = os.getenv(settings.UPDATE_HEALTH_NONCE, "")
    return nonce if os.getenv(settings.UPDATE_CHILD_FLAG) == settings.UPDATE_CHILD_VALUE and re.fullmatch(r"[0-9a-f]{32}", nonce) else None


def acknowledge_manual_stop(root):
    from app.updates.store import write_state

    nonce = worker_nonce()
    if nonce is None:
        return True
    try:
        write_state(Path(root) / STOP_ACK, {"nonce": nonce, "manual": True})
        return True
    except (OSError, ValueError):
        logger.warning("Не удалось подтвердить остановку; команда Stop сохранена.")
        return False


def manual_stop_acknowledged(root, nonce):
    from app.updates.store import load_state

    if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
        return False
    try:
        data = load_state(Path(root) / STOP_ACK)
        return set(data) == {"nonce", "manual"} and data.get("nonce") == nonce and data.get("manual") is True
    except (OSError, ValueError):
        return False


def request_worker_stop(root, nonce):
    from app.updates.store import write_state

    if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ValueError("Worker stop requires the current generation")
    write_state(Path(root) / WORKER_STOP_REQUEST, {"nonce": nonce, "action": "stop"})


def worker_stop_requested(root):
    from app.updates.store import load_state

    nonce = worker_nonce()
    if nonce is None:
        return False
    path = Path(root) / WORKER_STOP_REQUEST
    try:
        if load_state(path) != {"nonce": nonce, "action": "stop"}:
            return False
        path.unlink()
        return True
    except (OSError, ValueError):
        return False


def finish_process():
    stop_main_thread()


def stop_main_thread():
    from app.shutdown import request_exit

    logger.info("Получена команда остановки. Завершаю работу...")
    acknowledge_manual_stop(Path.cwd())
    request_exit(manual=True)


def watch_stop_requests(root, on_stop=stop_main_thread, poll=STOP_POLL_SECONDS):
    def loop():
        while True:
            if stop_requested(root):
                on_stop()
                return
            if worker_stop_requested(root):
                from app.shutdown import request_exit

                request_exit(exit_code=1)
                return
            time.sleep(poll)

    thread = threading.Thread(target=loop, name="cxh-stop-watch", daemon=True)
    thread.start()
    return thread


def lock_held(path):
    path = Path(path)
    if not path.exists():
        return False
    try:
        handle = path.open("a+b")
    except OSError:
        return False
    try:
        SingleInstanceGuard._prepare_lock_byte(handle)
        try:
            SingleInstanceGuard._lock(handle)
        except OSError:
            return True
        SingleInstanceGuard._unlock(handle)
        return False
    finally:
        handle.close()


def instance_running(root):
    return any(lock_held(Path(root) / lock) for lock in INSTANCE_LOCKS)


def stop_running_bot(root, timeout=STOP_WAIT_SECONDS, poll=0.5, output=print):
    if not instance_running(root):
        clear_stop_request(root)
        output("CXH FP не запущен. / CXH FP is not running.")
        return 0
    request_stop(root)
    output("Отправил команду остановки, жду завершения... / Stopping...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not instance_running(root):
            output("CXH FP остановлен. / CXH FP stopped.")
            return 0
        time.sleep(poll)
    output(
        f"CXH FP не остановился за {int(timeout)} с. Проверьте журнал logs/log.log. "
        "/ CXH FP did not stop in time."
    )
    return 1
