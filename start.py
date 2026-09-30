from app.console_encoding import configure_terminal
import subprocess
import sys

from app.constants.runtime import PROJECT_ROOT
from app.installer.environment import (
    environment_python,
    verify_environment,
    SetupFailure,
)


def main():
    configure_terminal()
    executable = environment_python(PROJECT_ROOT)
    if not executable.is_file():
        print("Run setup.py first / Сначала запустите setup.py")
        return 1
    try:
        verify_environment(executable, PROJECT_ROOT)
        return subprocess.call(
            [str(executable), str(PROJECT_ROOT / "main.py"), *sys.argv[1:]],
            cwd=PROJECT_ROOT,
        )
    except KeyboardInterrupt:
        return 0
    except (OSError, SetupFailure):
        print("Check .venv with setup.py / Проверьте окружение через setup.py")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
