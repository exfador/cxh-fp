import shutil
import textwrap
import warnings
from datetime import datetime
from getpass import GetPassWarning, getpass

from app.constants.branding import PROJECT_NAME, DEVELOPER_URL
from app.constants.runtime import VERSION
from app.constants.setup import SETUP_STEP_COUNT
from app.constants.setup_text import (
    SETUP_TEXT,
    LANGUAGE_OPTIONS,
    LANGUAGE_PROMPT,
    LANGUAGE_CHOICES,
    LANGUAGE_ERROR,
)
from app.constants.installer import TERMINAL_WIDTH, MINIMUM_WIDTH
from app.constants.terminal_style import (
    RESET,
    CYAN,
    MUTED,
    BOLD,
    WHITE,
    STATUS_COLORS,
    STATUS_LABELS,
    ERROR_KEYS,
    WARNING_KEYS,
    INFO_KEYS,
)
from app.terminal_colors import supports_color


class SetupConsole:
    def __init__(
        self,
        reader=input,
        secret_reader=getpass,
        writer=print,
        language="ru",
        color=None,
        clock=datetime.now,
    ):
        self.reader = reader
        self.secret_reader = secret_reader
        self.writer = writer
        self.language = language
        self.color = False if color is False else supports_color(force=color is True)
        self.clock = clock
        self.width = max(
            MINIMUM_WIDTH, min(TERMINAL_WIDTH, shutil.get_terminal_size().columns)
        )

    def paint(self, text, color):
        return f"{color}{text}{RESET}" if self.color else text

    def text(self, key, **values):
        return SETUP_TEXT[self.language][key].format(**values)

    def say(self, key, **values):
        text = self.text(key, **values)
        if key in WARNING_KEYS:
            self.event(text, "warn")
        elif key in ERROR_KEYS or key.endswith("_error"):
            self.event(text, "error")
        elif key in INFO_KEYS:
            self.event(text, "info")
        else:
            self.write(text)

    def write(self, text, color=""):
        for line in text.split("\n"):
            for part in textwrap.wrap(
                line, self.width - 4, replace_whitespace=False
            ) or [""]:
                self.writer("  " + self.paint(part, color) if color else "  " + part)

    def event(self, text, status="info"):
        timestamp = self.clock().strftime("%H:%M:%S")
        label = STATUS_LABELS[self.language][status]
        prefix = f"{timestamp}  {label:<8}  "
        if self.width - 2 - len(prefix) < 16:
            self.write(f"{timestamp}  {label}", STATUS_COLORS[status])
            self.write(text)
            return
        width = max(8, self.width - 2 - len(prefix))
        lines = [
            part
            for line in text.splitlines()
            for part in textwrap.wrap(line, width) or [""]
        ]
        header = (
            self.paint(timestamp, MUTED)
            + "  "
            + self.paint(f"{label:<8}", STATUS_COLORS[status])
            + "  "
        )
        for index, line in enumerate(lines):
            self.writer("  " + (header if index == 0 else " " * len(prefix)) + line)

    def input_prefix(self, secret=False):
        label = f" [{self.text('hidden')}]" if secret else ""
        return "  " + self.paint("›", CYAN + BOLD) + self.paint(label, MUTED) + " "

    def choose_language(self):
        self.write(f"\n{PROJECT_NAME}  /  {VERSION}", CYAN + BOLD)
        self.write(f"\n{LANGUAGE_PROMPT}", WHITE + BOLD)
        self.options(LANGUAGE_OPTIONS)
        while True:
            value = self.reader(self.input_prefix()).strip().lower()
            if value in LANGUAGE_CHOICES:
                self.language = LANGUAGE_CHOICES[value]
                return self.language
            self.event(LANGUAGE_ERROR, "error")

    def banner(self, subtitle=None):
        self.writer("")
        self.rule("╭", "╮")
        for text, color in (
            (f"{PROJECT_NAME}  /  {VERSION}", CYAN + BOLD),
            (subtitle or self.text("subtitle"), WHITE),
            (DEVELOPER_URL, MUTED),
        ):
            self.box_line(text, color)
        self.rule("╰", "╯")
        self.writer("")

    def rule(self, left, right):
        self.writer("  " + self.paint(left + "─" * (self.width - 6) + right, MUTED))

    def box_line(self, text, color):
        for line in textwrap.wrap(text, self.width - 8):
            padding = " " * (self.width - 8 - len(line))
            self.writer(
                "  "
                + self.paint("│ ", MUTED)
                + self.paint(line, color)
                + padding
                + self.paint(" │", MUTED)
            )

    def step(self, number, title):
        self.writer("")
        progress = (
            "[ "
            + " ".join(
                "+" if step < number else ">" if step == number else "-"
                for step in range(1, SETUP_STEP_COUNT + 1)
            )
            + " ]"
        )
        self.write(f"{number:02d} / {SETUP_STEP_COUNT:02d}  {title}", CYAN + BOLD)
        self.write(progress, CYAN)
        self.write("─" * (self.width - 4), MUTED)

    def success(self, key, **values):
        self.event(self.text(key, **values), "ok")

    def options(self, text):
        self.writer("")
        for line in text.splitlines():
            number, separator, label = line.partition("  ")
            if separator and number.isdigit():
                prefix = f"[{number}] "
                parts = textwrap.wrap(label, self.width - 4 - len(prefix)) or [""]
                for index, part in enumerate(parts):
                    self.writer(
                        "  "
                        + (
                            self.paint(prefix, CYAN + BOLD)
                            if index == 0
                            else " " * len(prefix)
                        )
                        + part
                    )
            else:
                self.write(line)
        self.writer("")

    def read(self, prompt, secret=False):
        self.writer("")
        self.write(prompt, WHITE)
        return self.read_value(secret)

    def read_value(self, secret=False):
        reader = self.secret_reader if secret else self.reader
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            return reader(self.input_prefix(secret)).strip()

    def choice(self, key, choices):
        while True:
            self.options(self.text(key))
            value = self.read_value()
            if value in choices:
                return value
            self.say("choice_error")

    def validated(self, prompt, validator, error, secret=False):
        while True:
            value = self.read(prompt, secret)
            if validator(value):
                return value
            self.event(error, "error")
