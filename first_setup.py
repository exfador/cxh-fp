from configparser import ConfigParser
from pathlib import Path

import telebot

from app.constants.runtime import MAIN_CONFIG, RESPONSE_CONFIG, DELIVERY_CONFIG
from app.setup.defaults import default_config
from app.setup.steps import (
    configure_funpay,
    configure_telegram,
    configure_password,
    configure_funpay_proxy,
    read_proxy,
)
from app.setup.storage import write_setup_config
from app.setup.terminal import SetupConsole
from Utils.config_loader import load_main_config


def create_configs():
    for filename in (RESPONSE_CONFIG, DELIVERY_CONFIG):
        destination = Path(filename)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.touch(exist_ok=True)


def create_config_obj(settings) -> ConfigParser:
    config = ConfigParser(delimiters=(":",), interpolation=None)
    config.optionxform = str
    config.read_dict(settings)
    return config


def contains_russian(text: str) -> bool:
    return any("А" <= character <= "я" or character in "Ёё" for character in text)


def input_proxy(set_telebot_proxy: bool = False) -> str | None:
    return read_proxy(SetupConsole(), set_telebot_proxy)


def setup_telegram_proxy():
    console = SetupConsole()
    config = load_main_config(MAIN_CONFIG)
    console.language = config["Other"].get("language", "ru")
    console.banner()
    while True:
        proxy = read_proxy(console, set_telebot_proxy=True)
        try:
            username = telebot.TeleBot(config["Telegram"]["token"]).get_me().username
        except Exception:
            console.say("token_error")
            continue
        config["Telegram"]["proxy"] = proxy or ""
        write_setup_config(config, MAIN_CONFIG, replace=True)
        console.success("proxy_done", username=username)
        return


def first_setup(language=None, console=None):
    console = console or SetupConsole(language=language or "ru")
    if language is None:
        console.choose_language()
    else:
        console.language = language
    console.banner()
    if Path(MAIN_CONFIG).exists():
        console.say("existing")
        return
    console.say("intro")
    config = create_config_obj(default_config)
    config["Other"]["language"] = console.language
    configure_funpay(config, console)
    configure_telegram(config, console)
    configure_password(config, console)
    configure_funpay_proxy(config, console)
    console.write("\n" + console.text("review"))
    console.say("review_body")
    if console.choice("save", ("1", "2")) == "2":
        raise KeyboardInterrupt
    create_configs()
    write_setup_config(config, MAIN_CONFIG)
    console.success("complete")


def main():
    import argparse
    import os
    from getpass import GetPassWarning
    from app.constants.runtime import PROJECT_ROOT

    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=("ru", "en"))
    parser.add_argument("--no-color", action="store_true")
    options = parser.parse_args()
    os.chdir(PROJECT_ROOT)
    console = SetupConsole(
        language=options.language or "ru", color=False if options.no_color else None
    )
    try:
        first_setup(options.language, console)
        return 0
    except (KeyboardInterrupt, EOFError):
        console.say("cancelled")
    except GetPassWarning:
        console.say("secret_unavailable")
    except OSError:
        console.say("failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
