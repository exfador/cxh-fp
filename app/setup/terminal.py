import os
import shutil
import sys
import textwrap
import warnings
from getpass import GetPassWarning, getpass

from app.constants.branding import PROJECT_NAME, DEVELOPER_URL
from app.constants.runtime import VERSION
from app.constants.setup import INPUT_PROMPT, SETUP_STEP_COUNT
from app.constants.setup_text import (
    SETUP_TEXT,
    LANGUAGE_OPTIONS,
    LANGUAGE_PROMPT,
    LANGUAGE_CHOICES,
    LANGUAGE_ERROR,
)
from app.constants.installer import (
    TERMINAL_WIDTH,
    MINIMUM_WIDTH,
    ANSI_CYAN,
    ANSI_GREEN,
    ANSI_RESET,
)


class SetupConsole:
    def __init__(
        self,
        reader=input,
        secret_reader=getpass,
        writer=print,
        language="ru",
        color=None,
    ):
        self.reader = reader
        self.secret_reader = secret_reader
        self.writer = writer
        self.language = language
        self.color = supports_color() if color is None else color
        self.width = max(
            MINIMUM_WIDTH, min(TERMINAL_WIDTH, shutil.get_terminal_size().columns)
        )

    def text(self, key, **values):
        return SETUP_TEXT[self.language][key].format(**values)

    def say(self, key, **values):
        self.write(self.text(key, **values))

    def write(self, text, color=""):
        for line in text.split("\n"):
            for part in textwrap.wrap(
                line, self.width - 4, replace_whitespace=False
            ) or [""]:
                prefix, suffix = (
                    (color, ANSI_RESET) if self.color and color else ("", "")
                )
                self.writer(f"  {prefix}{part}{suffix}")

    def choose_language(self):
        self.write(f"\n{PROJECT_NAME} / {VERSION}", ANSI_CYAN)
        self.write(f"\n{LANGUAGE_PROMPT}\n{LANGUAGE_OPTIONS}")
        while True:
            value = self.reader(INPUT_PROMPT).strip().lower()
            if value in LANGUAGE_CHOICES:
                self.language = LANGUAGE_CHOICES[value]
                return self.language
            self.write(LANGUAGE_ERROR)

    def banner(self):
        self.write("\n" + "-" * (self.width - 4), ANSI_CYAN)
        self.write(f"{PROJECT_NAME} / {VERSION}", ANSI_CYAN)
        self.say("subtitle")
        self.write(DEVELOPER_URL)
        self.write("-" * (self.width - 4) + "\n", ANSI_CYAN)

    def step(self, number, title):
        self.write(f"\n[{number}/{SETUP_STEP_COUNT}] {title}", ANSI_CYAN)
        self.write("-" * (self.width - 4))

    def success(self, key, **values):
        self.write(f"OK  {self.text(key, **values)}", ANSI_GREEN)

    def read(self, prompt, secret=False):
        self.write(prompt)
        reader = self.secret_reader if secret else self.reader
        prefix = f"  > [{self.text('hidden')}] " if secret else INPUT_PROMPT
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            return reader(prefix).strip()

    def choice(self, key, choices):
        while True:
            value = self.read(self.text(key))
            if value in choices:
                return value
            self.say("choice_error")

    def validated(self, prompt, validator, error, secret=False):
        while True:
            value = self.read(prompt, secret)
            if validator(value):
                return value
            self.write(error)


def supports_color():
    if (
        not sys.stdout.isatty()
        or "NO_COLOR" in os.environ
        or os.getenv("TERM") == "dumb"
    ):
        return False
    return os.name != "nt" or bool(os.getenv("WT_SESSION") or os.getenv("TERM"))
