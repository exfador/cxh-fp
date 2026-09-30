import sys

from app.constants.console import CONSOLE_ENCODING, CONSOLE_OUTPUT_ERRORS


def configure_terminal():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding=CONSOLE_ENCODING, errors=CONSOLE_OUTPUT_ERRORS)
