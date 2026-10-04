import atexit
import copy
import functools
import logging
import logging.config
import logging.handlers
import queue
import sys

from Utils.logging_support.constants import (
    LOGGER_NAMES,
    PAYLOAD_LOGGER_NAMES,
    LOG_QUEUE_SIZE,
    QUEUE_OVERFLOW_MESSAGE,
)
from Utils.logging_support.files import RecoveringFileHandler, log_path
from Utils.logging_support.formatters import (
    ConsoleFilter,
    CLILoggerFormatter,
    FileLoggerFormatter,
    safe_message,
)


class SafeQueueHandler(logging.handlers.QueueHandler):
    def __init__(self, runtime):
        super().__init__(runtime.queue)
        self.runtime = runtime
        self.overflow = False

    def prepare(self, record):
        cloned = copy.copy(record)
        cloned.msg, cloned.args = safe_message(record), ()
        cloned.exc_text = None
        return cloned

    def enqueue(self, record):
        try:
            self.queue.put_nowait(record)
            self.overflow = False
        except queue.Full:
            if not self.overflow:
                self.runtime.warn(QUEUE_OVERFLOW_MESSAGE)
            self.overflow = True


class SafeConsoleHandler(logging.StreamHandler):
    def handleError(self, record):
        self.setLevel(logging.CRITICAL + 1)


class LoggingRuntime:
    def __init__(self, root, stream=None):
        self.stream = stream or sys.stderr
        self.queue = queue.Queue(maxsize=LOG_QUEUE_SIZE)
        self.handler = SafeQueueHandler(self)
        self.console = SafeConsoleHandler(self.stream)
        self.console.setLevel(logging.INFO)
        self.console.addFilter(ConsoleFilter())
        self.console.setFormatter(CLILoggerFormatter(stream=self.stream))
        self.file = RecoveringFileHandler(log_path(root), self.warn)
        self.file.setLevel(logging.DEBUG)
        self.file.setFormatter(FileLoggerFormatter())
        self.listener = logging.handlers.QueueListener(
            self.queue, self.console, self.file, respect_handler_level=True
        )
        self.previous = []
        self.started = False

    def warn(self, message):
        try:
            self.stream.write(message + "\n")
            self.stream.flush()
        except (OSError, ValueError):
            return

    def start(self):
        for name in ("", *LOGGER_NAMES):
            logger = logging.getLogger(name)
            self.previous.append(
                (logger, logger.handlers[:], logger.level, logger.propagate)
            )
        self.attach()
        guard_configuration()
        self.listener.start()
        self.started = True
        atexit.register(self.stop)
        return self

    def attach(self):
        for name in ("", *LOGGER_NAMES):
            logger = logging.getLogger(name)
            logger.handlers = [self.handler] if not name else []
            logger.setLevel(
                logging.WARNING if name in PAYLOAD_LOGGER_NAMES else logging.DEBUG
            )
            logger.propagate = bool(name)
            logger.disabled = False

    def restore(self, disabled):
        self.attach()
        for name, was_disabled in disabled.items():
            logger = logging.Logger.manager.loggerDict.get(name)
            if isinstance(logger, logging.Logger) and not was_disabled:
                logger.disabled = False

    def flush(self):
        if self.started:
            self.queue.join()
        self.file.flush()

    def stop(self):
        if not self.started:
            return
        for logger, handlers, level, propagate in self.previous:
            logger.handlers, logger.level, logger.propagate = handlers, level, propagate
        self.queue.join()
        self.listener.stop()
        self.file.close()
        self.console.close()
        self.started = False
        atexit.unregister(self.stop)


def current_runtime():
    for handler in logging.getLogger().handlers:
        if isinstance(handler, SafeQueueHandler):
            return handler.runtime
    return None


def guarded_configuration(original):
    @functools.wraps(original)
    def configure(*args, **kwargs):
        runtime = current_runtime()
        disabled = {
            name: logger.disabled
            for name, logger in list(logging.Logger.manager.loggerDict.items())
            if isinstance(logger, logging.Logger)
        }
        try:
            return original(*args, **kwargs)
        finally:
            if runtime is not None and runtime.started:
                runtime.restore(disabled)

    configure.cxh_logging_guard = True
    return configure


def guard_configuration():
    for name in ("dictConfig", "fileConfig"):
        original = getattr(logging.config, name)
        if not getattr(original, "cxh_logging_guard", False):
            setattr(logging.config, name, guarded_configuration(original))
