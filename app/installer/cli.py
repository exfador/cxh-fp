from app.console_encoding import configure_terminal
import argparse
import platform
import subprocess

from app.constants.runtime import PROJECT_ROOT
from app.constants.installer import MENU_STEPS
from app.constants.branding import PROJECT_NAME
from app.constants.setup import BOT_USERNAME_EXAMPLE
from app.setup.terminal import SetupConsole
from app.installer.environment import (
    SetupFailure,
    prepare_dependencies,
    validate_system,
    run_process,
)


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=f"{PROJECT_NAME} setup / Настройка")
    parser.add_argument(
        "--language", "--lang", choices=("ru", "en"), help="Interface language / Язык"
    )
    parser.add_argument("--no-color", action="store_true", help="Plain terminal output")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--check", action="store_true", help="Check Python and platform without changes"
    )
    modes.add_argument(
        "--preview",
        action="store_true",
        help="Show the wizard without saving or installing",
    )
    return parser.parse_args(argv)


def preview(console):
    console.say("preview")
    for number, key in enumerate(MENU_STEPS, start=1):
        console.step(number, console.text(key))
        if number == 2:
            console.say("botfather", name=PROJECT_NAME, username=BOT_USERNAME_EXAMPLE)
    console.write("\n" + console.text("review"))
    console.say("review_body")


def execute(options, console, root):
    console.banner()
    console.say("environment")
    console.write(f"{platform.system()} / Python {platform.python_version()}")
    validate_system()
    if options.check:
        console.success("check_ok")
        return 0
    if options.preview:
        preview(console)
        return 0
    executable = prepare_dependencies(root, console)
    command = [executable, root / "first_setup.py", "--language", console.language]
    if options.no_color:
        command.append("--no-color")
    run_process(command, root, timeout=None)
    console.say("launch", command="python start.py")
    return 0


def main(argv=None, console=None, root=PROJECT_ROOT):
    configure_terminal()
    options = arguments(argv)
    console = console or SetupConsole(color=False if options.no_color else None)
    try:
        if options.language:
            console.language = options.language
        else:
            console.choose_language()
        return execute(options, console, root)
    except (KeyboardInterrupt, EOFError):
        console.say("cancelled")
    except SetupFailure as error:
        console.say(str(error))
    except (OSError, subprocess.SubprocessError):
        console.say("install_error")
    return 1
