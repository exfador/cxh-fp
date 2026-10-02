import os
import sys


def enable_windows_color(stream):
    try:
        import ctypes
        import msvcrt
        from ctypes import wintypes

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
        return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError, ValueError):
        return False


def supports_color(stream=None, force=False):
    stream = sys.stdout if stream is None else stream
    preference = os.getenv("CXH_CONSOLE_COLOR")
    if not force and preference == "never":
        return False
    force = force or preference == "always"
    if not force and ("NO_COLOR" in os.environ or os.getenv("TERM") == "dumb"):
        return False
    try:
        interactive = getattr(stream, "isatty", lambda: False)()
    except (OSError, ValueError):
        return False
    if not interactive:
        return force
    return os.name != "nt" or enable_windows_color(stream)


def color_arguments(arguments):
    choices = {arg for arg in arguments if arg in {"--color", "--no-color"}}
    if len(choices) > 1:
        raise ValueError("Choose either --color or --no-color")
    if choices:
        os.environ["CXH_CONSOLE_COLOR"] = "always" if "--color" in choices else "never"
    return [arg for arg in arguments if arg not in choices]
