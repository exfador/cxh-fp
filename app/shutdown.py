import inspect
from contextlib import nullcontext
import logging
import os
import re
import signal
import sys
import threading
import time
from types import FunctionType, MethodType
from app.constants import update_runtime as settings


logger = logging.getLogger("main")


def managed_runtime():
    return (
        os.getenv(settings.UPDATE_CHILD_FLAG) == settings.UPDATE_CHILD_VALUE
        and re.fullmatch(r"[0-9a-f]{32}", os.getenv(settings.UPDATE_HEALTH_NONCE, "")) is not None
    )


def resource_protocol(resource):
    try:
        fields = vars(resource)
    except TypeError:
        return None
    stop, closed = fields.get("stop_event"), fields.get("closed_event")
    if type(stop) is not threading.Event or type(closed) is not threading.Event or stop is closed:
        return None
    close = inspect.getattr_static(resource, "close", None)
    if isinstance(close, FunctionType):
        close = MethodType(close, resource)
    if not isinstance(close, MethodType) or close.__self__ is not resource:
        return None
    return stop, closed, close


class ShutdownCoordinator:
    def __init__(self, grace_seconds=60, poll_seconds=0.2):
        self.lock = threading.RLock()
        self.cardinal = None
        self.resources = {}
        self.requested = threading.Event()
        self.closed = threading.Event()
        self.manual = False
        self.requested_exit = None
        self.requested_restart = False
        self.restart_executed = False
        self.thread = None
        self.grace_seconds, self.poll_seconds = grace_seconds, poll_seconds

    def bind(self, cardinal):
        with self.lock:
            if self.cardinal is not None and self.cardinal is not cardinal:
                raise RuntimeError("A different Cardinal is already bound to shutdown")
            self.cardinal = cardinal
            if self.requested.is_set():
                vars(cardinal)["_process_stopping"] = True
        self.discover()

    def register(self, resource):
        protocol = resource_protocol(resource)
        if protocol is None:
            return False
        with self.lock:
            self.resources.setdefault(id(resource), (resource, *protocol))
            if self.requested.is_set():
                protocol[0].set()
        return True

    def discover(self):
        with self.lock:
            cardinal = self.cardinal
        if cardinal is not None:
            for resource in tuple(vars(cardinal).values()):
                self.register(resource)

    def request(self, exit_code=None, manual=False, restart=False):
        with self.lock:
            first = not self.requested.is_set()
            if manual:
                self.manual = True
            if restart and self.requested_exit is None and not self.manual:
                if managed_runtime():
                    self.requested_exit = settings.UPDATE_RESTART_EXIT_CODE
                else:
                    self.requested_restart = True
            if exit_code is not None and not self.manual and not self.requested_restart and self.requested_exit is None:
                self.requested_exit = exit_code
            self.requested.set()
            if self.cardinal is not None:
                vars(self.cardinal)["_process_stopping"] = True
        self.discover()
        with self.lock:
            for _, stop, _, _ in self.resources.values():
                stop.set()
        return first

    def exit_code(self, fallback):
        with self.lock:
            return 0 if self.manual else (self.requested_exit if self.requested_exit is not None else fallback)

    def restart_pending(self):
        with self.lock:
            return self.requested_restart and not self.manual and not self.restart_executed

    def execute_restart(self):
        if threading.current_thread() is not threading.main_thread() or not self.closed.is_set():
            raise RuntimeError("Restart requires completed shutdown on the main thread")
        from app.stop_control import acknowledge_manual_stop, stop_requested
        from pathlib import Path

        if stop_requested(Path.cwd()):
            acknowledge_manual_stop(Path.cwd())
            self.request(manual=True)
        with self.lock:
            if not self.restart_pending():
                return False
            self.restart_executed = True
            os.execl(sys.executable, sys.executable, *sys.argv)
        return False

    def finish(self):
        previous = None
        if threading.current_thread() is threading.main_thread():
            previous = signal.signal(signal.SIGINT, self._manual_signal)
        try:
            self._finish()
        finally:
            if previous is not None:
                signal.signal(signal.SIGINT, previous)

    def _manual_signal(self, number=None, frame=None):
        from app.stop_control import acknowledge_manual_stop
        from pathlib import Path

        acknowledge_manual_stop(Path.cwd())
        self.request(manual=True)

    def _finish(self):
        self.request()
        with self.lock:
            if self.thread is None:
                self.thread = threading.Thread(target=self._drain, name="cxh-shutdown", daemon=False)
                self.thread.start()
        deadline = time.monotonic() + self.grace_seconds
        warned = False
        while True:
            try:
                if self.closed.wait(self.poll_seconds):
                    return
                if not warned and time.monotonic() >= deadline:
                    logger.warning("Остановка ещё выполняется: ожидаю завершения операций. Блокировки сохранены; повторный запуск не разрешён.")
                    warned = True
            except KeyboardInterrupt:
                self._manual_signal()

    def _drain(self):
        try:
            if self.cardinal is not None:
                activation_lock = inspect.getattr_static(self.cardinal, "plugin_activation_lock", None)
                barrier = activation_lock if type(activation_lock) is type(threading.RLock()) else nullcontext()
                with barrier:
                    self.discover()
                self.cardinal.stop()
                self.discover()
            with self.lock:
                resources = tuple(self.resources.values())
            for _, _, closed, close in resources:
                if not closed.is_set():
                    close()
            for _, _, closed, _ in resources:
                closed.wait()
        except BaseException as error:
            logger.error("Не удалось завершить остановку (%s). Блокировки сохранены.", type(error).__name__)
            return
        self.closed.set()


_coordinator = ShutdownCoordinator()


def coordinator():
    return _coordinator


def request_exit(exit_code=None, manual=False):
    import _thread

    if _coordinator.request(exit_code=exit_code, manual=manual):
        _thread.interrupt_main()


def request_restart():
    import _thread

    if _coordinator.request(restart=True):
        _thread.interrupt_main()
