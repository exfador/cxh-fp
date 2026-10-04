from app.console_encoding import configure_terminal
import subprocess
import sys
import time

from app.constants.runtime import PROJECT_ROOT
from app.installer.environment import (
    environment_python,
    verify_environment,
    SetupFailure,
)

INTERRUPT_WAIT_SECONDS = 30


def wait_after_interrupt(process, timeout=INTERRUPT_WAIT_SECONDS):
    deadline = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < deadline:
        try:
            process.wait(timeout=0.5)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            continue


def stopped_by_user(process):
    wait_after_interrupt(process)
    from app.console_prompt import schedule_batch_answer

    try:
        schedule_batch_answer(PROJECT_ROOT)
    except Exception:
        pass
    return 0


def main():
    configure_terminal()
    executable = environment_python(PROJECT_ROOT)
    if not executable.is_file():
        print("Run setup.py first / Сначала запустите setup.py")
        return 1
    try:
        verify_environment(executable, PROJECT_ROOT)
        process = subprocess.Popen(
            [str(executable), str(PROJECT_ROOT / "main.py"), *sys.argv[1:]],
            cwd=PROJECT_ROOT,
        )
    except KeyboardInterrupt:
        return 0
    except (OSError, SetupFailure):
        print("Check .venv with setup.py / Проверьте окружение через setup.py")
        return 1
    try:
        return process.wait()
    except KeyboardInterrupt:
        return stopped_by_user(process)


if __name__ == "__main__":
    raise SystemExit(main())
