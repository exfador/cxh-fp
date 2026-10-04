import os
import subprocess
import sys
import time

ANSWER_DELAY_SECONDS = 0.6
BATCH_NAME = "start.bat"


def batch_shell_pid():
    import psutil

    try:
        parents = psutil.Process().parents()
    except psutil.Error:
        return None
    for process in parents:
        try:
            if process.name().lower() != "cmd.exe":
                continue
            arguments = [part.strip(' "').lower() for part in process.cmdline()]
        except psutil.Error:
            return None
        launched_batch = any(part.endswith(BATCH_NAME) for part in arguments)
        return process.pid if launched_batch and "/c" in arguments else None
    return None


def schedule_batch_answer(root):
    if os.name != "nt":
        return False
    pid = batch_shell_pid()
    if pid is None:
        return False
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [sys.executable, "-m", "app.console_prompt", str(pid)],
        cwd=root,
        creationflags=flags,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def key_records(text):
    import ctypes
    from ctypes import wintypes

    class KeyEvent(ctypes.Structure):
        _fields_ = [
            ("bKeyDown", wintypes.BOOL),
            ("wRepeatCount", wintypes.WORD),
            ("wVirtualKeyCode", wintypes.WORD),
            ("wVirtualScanCode", wintypes.WORD),
            ("uChar", wintypes.WCHAR),
            ("dwControlKeyState", wintypes.DWORD),
        ]

    class EventUnion(ctypes.Union):
        _fields_ = [("KeyEvent", KeyEvent)]

    class InputRecord(ctypes.Structure):
        _fields_ = [("EventType", wintypes.WORD), ("Event", EventUnion)]

    records = []
    for char in text:
        for pressed in (True, False):
            record = InputRecord()
            record.EventType = 1
            record.Event.KeyEvent.bKeyDown = pressed
            record.Event.KeyEvent.wRepeatCount = 1
            record.Event.KeyEvent.uChar = char
            record.Event.KeyEvent.wVirtualKeyCode = 0x0D if char == "\r" else ord(char)
            records.append(record)
    return (InputRecord * len(records))(*records)


def answer(pid, delay=ANSWER_DELAY_SECONDS):
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.FreeConsole()
    time.sleep(delay)
    if not kernel.AttachConsole(pid):
        return False
    handle = kernel.CreateFileW("CONIN$", 0xC0000000, 3, None, 3, 0, None)
    if handle in (None, wintypes.HANDLE(-1).value):
        return False
    records = key_records("Y\r")
    written = wintypes.DWORD()
    try:
        return bool(
            kernel.WriteConsoleInputW(
                handle, records, len(records), ctypes.byref(written)
            )
        )
    finally:
        kernel.CloseHandle(handle)
        kernel.FreeConsole()


if __name__ == "__main__":
    raise SystemExit(0 if answer(int(sys.argv[1])) else 1)
