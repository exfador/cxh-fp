from app.console_encoding import configure_terminal
import os
import sys
from pathlib import Path

from app.constants.update_runtime import UPDATE_CHILD_FLAG, UPDATE_CHILD_VALUE


def main():
    configure_terminal()
    from app.terminal_colors import color_arguments

    try:
        sys.argv[1:] = color_arguments(sys.argv[1:])
    except ValueError as error:
        print(str(error))
        return 2
    root = Path(__file__).resolve().parent
    os.chdir(root)
    if (
        os.getenv(UPDATE_CHILD_FLAG) != UPDATE_CHILD_VALUE
        and sys.argv[1:] in ([], ["run"])
        and (root / "configs/_main.cfg").exists()
    ):
        from app.updates.supervisor import main as supervise

        return supervise(root)
    from app.runtime_cli import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
