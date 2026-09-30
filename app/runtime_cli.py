import argparse
import os
from collections import deque
from pathlib import Path

from app.constants.runtime import PROJECT_ROOT, VERSION, MAIN_CONFIG
from app.constants.console import DEFAULT_TAIL_LINES, MAX_TAIL_LINES, TAIL_MAX_BYTES
from app.constants.branding import PROJECT_NAME


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=f"{PROJECT_NAME} / управление ботом")
    parser.add_argument(
        "--version", action="version", version=f"{PROJECT_NAME} {VERSION}"
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("run", help="Запустить бот / Start bot")
    commands.add_parser("status", help="Локальные файлы и журналы / Local status")
    logs = commands.add_parser("logs", help="Последние записи / Recent log entries")
    logs.add_argument("--lines", type=int, default=DEFAULT_TAIL_LINES)
    backup = commands.add_parser("backup", help="Резервная копия / Backup")
    backup.add_argument("action", choices=("create", "check"))
    return parser.parse_args(argv)


def show_status(root):
    from Utils.logging_support.files import log_path
    from Utils.backups.constants import BACKUP_PATH

    print(f"{PROJECT_NAME} / {VERSION}\n{root}")
    for name in (Path(MAIN_CONFIG), log_path(root).relative_to(root), BACKUP_PATH):
        path = root / name
        status = f"{path.stat().st_size:,} bytes" if path.is_file() else "missing"
        print(f"  {name}: {status}")
    return 0


def show_logs(root, lines):
    from Utils.logging_support.files import log_path
    from Utils.logging_support.formatters import clean_text, has_payload

    if not 1 <= lines <= MAX_TAIL_LINES:
        raise ValueError(f"--lines must be between 1 and {MAX_TAIL_LINES}")
    with log_path(root).open("rb") as handle:
        size = handle.seek(0, os.SEEK_END)
        handle.seek(max(0, size - TAIL_MAX_BYTES))
        content = handle.read().decode("utf-8", errors="replace")
    entries = (
        clean_text(line)
        for line in content.splitlines()
        if len(line.split(" | ", 3)) == 4
        and line.split(" | ", 3)[1].strip() != "DEBUG"
        and not has_payload(line)
    )
    print("\n".join(deque(entries, maxlen=lines)))
    return 0


def backup_command(root, action):
    from Utils.backups.service import BackupService

    service = BackupService(root)
    if action == "create":
        service.create()
    result = service.check()
    print(f"OK  backup.zip / {result['files']} files / {result['bytes']:,} bytes")
    return 0


def main(argv=None, root=PROJECT_ROOT):
    options = arguments(argv)
    if options.command in (None, "run"):
        from app.bootstrap import main as run

        return run()
    try:
        if options.command == "status":
            return show_status(root)
        if options.command == "logs":
            return show_logs(root, options.lines)
        return backup_command(root, options.action)
    except Exception as error:
        print(
            f"Operation failed ({type(error).__name__}). Check paths, permissions and the archive."
        )
        return 1
