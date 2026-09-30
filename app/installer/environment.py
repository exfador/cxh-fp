import subprocess
import sys
from pathlib import Path

from app.constants.installer import (
    ENVIRONMENT_NAME,
    PYTHON_PATHS,
    PYTHON_PROBE,
    SUPPORTED_PLATFORMS,
    SUPPORTED_PYTHON,
    PROCESS_TIMEOUT,
    PROBE_TIMEOUT,
)


class SetupFailure(Exception):
    pass


def environment_python(root, platform=None):
    platform = platform or sys.platform
    parts = PYTHON_PATHS["win32" if platform == "win32" else "posix"]
    return Path(root) / ENVIRONMENT_NAME / Path(*parts)


def validate_system(version=None, platform=None):
    if tuple(version or sys.version_info[:2]) != SUPPORTED_PYTHON:
        raise SetupFailure("python_error")
    if (platform or sys.platform) not in SUPPORTED_PLATFORMS:
        raise SetupFailure("platform_error")


def run_process(arguments, root, timeout=PROCESS_TIMEOUT, capture=False):
    return subprocess.run(
        [str(value) for value in arguments],
        cwd=root,
        check=True,
        timeout=timeout,
        capture_output=capture,
    )


def verify_environment(executable, root):
    try:
        run_process([executable, "-c", PYTHON_PROBE], root, PROBE_TIMEOUT, capture=True)
    except (OSError, subprocess.SubprocessError) as error:
        raise SetupFailure("environment_error") from error


def prepare_dependencies(root, console):
    directory = root / ENVIRONMENT_NAME
    executable = environment_python(root)
    console.say("venv")
    if not directory.exists():
        run_process([sys.executable, "-m", "venv", directory], root)
    if not (directory / "pyvenv.cfg").is_file() or not executable.is_file():
        raise SetupFailure("environment_error")
    verify_environment(executable, root)
    install_dependencies(executable, root, console)
    console.success("ready")
    return executable


def install_dependencies(executable, root, console):
    console.say("dependencies")
    run_process(
        [
            executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--quiet",
            "--progress-bar",
            "off",
            "--require-hashes",
            "-r",
            root / "requirements.txt",
        ],
        root,
    )
    run_process([executable, "-m", "pip", "check"], root)
