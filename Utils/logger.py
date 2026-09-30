from pathlib import Path

from app.constants.runtime import PROJECT_ROOT
from Utils.logging_support.formatters import CLILoggerFormatter, FileLoggerFormatter
from Utils.logging_support.runtime import LoggingRuntime, current_runtime

__all__ = ("configure_logging", "CLILoggerFormatter", "FileLoggerFormatter")


def configure_logging(root=PROJECT_ROOT, stream=None):
    existing = current_runtime()
    if existing is not None:
        existing.stop()
    return LoggingRuntime(Path(root), stream).start()


def flush_logs():
    runtime = current_runtime()
    if runtime is not None:
        runtime.flush()


def stop_logging():
    runtime = current_runtime()
    if runtime is not None:
        runtime.stop()
