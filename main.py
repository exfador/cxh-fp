import os
import sys
from pathlib import Path

from app.constants.update_runtime import UPDATE_CHILD_FLAG, UPDATE_CHILD_VALUE


def main():
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
