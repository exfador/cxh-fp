import _thread
import json
import logging
import os
import threading
import time
from pathlib import Path

from Utils.single_instance_guard import SingleInstanceGuard

STOP_REQUEST = Path("run/stop.request")
STOP_POLL_SECONDS = 1.0
STOP_GRACE_SECONDS = 20.0
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
    clear_stop_request(root)
    return True


def finish_process():
    from Utils.logger import stop_logging

    stop_logging()
    os._exit(0)


def stop_main_thread():
    logger.info("Получена команда остановки. Завершаю работу...")
    timer = threading.Timer(STOP_GRACE_SECONDS, finish_process)
    timer.daemon = True
    timer.start()
    _thread.interrupt_main()


def watch_stop_requests(root, on_stop=stop_main_thread, poll=STOP_POLL_SECONDS):
    def loop():
        while True:
            if stop_requested(root):
                on_stop()
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
