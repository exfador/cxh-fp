import os
import sys

from app.constants.console import (
    CONSOLE_ENCODING,
    CONSOLE_EXTENDED_FLAGS,
    CONSOLE_OUTPUT_ERRORS,
    CONSOLE_QUICK_EDIT,
)


def without_quick_edit(mode):
    return (mode | CONSOLE_EXTENDED_FLAGS) & ~CONSOLE_QUICK_EDIT


def disable_quick_edit(stream=None):
    if os.name != "nt":
        return False
    try:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        stream = sys.stdin if stream is None else stream
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetConsoleMode.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        )
        kernel.GetConsoleMode.restype = wintypes.BOOL
        kernel.SetConsoleMode.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.SetConsoleMode.restype = wintypes.BOOL
        handle = msvcrt.get_osfhandle(stream.fileno())
        mode = wintypes.DWORD()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, without_quick_edit(mode.value)))
    except (AttributeError, OSError, ValueError):
        return False


def configure_terminal():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding=CONSOLE_ENCODING, errors=CONSOLE_OUTPUT_ERRORS)
    disable_quick_edit()
