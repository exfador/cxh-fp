import hmac
import telebot
import requests

from app.constants import setup as settings
from app.constants.branding import PROJECT_NAME
from app.setup.validation import (
    valid_golden_key,
    valid_user_agent,
    valid_bot_token,
    valid_bot_username,
    valid_password,
)
from Utils.cardinal_tools import validate_proxy, build_proxy, hash_password
from app.setup.connection_errors import report_bot_error


def configure_funpay(config, console):
    console.step(1, console.text("step_funpay"))
    config["FunPay"]["golden_key"] = console.validated(
        console.text("golden_key"),
        valid_golden_key,
        console.text("golden_key_error"),
        secret=True,
    )
    user_agent = console.validated(
        console.text("user_agent"),
        valid_user_agent,
        console.text("user_agent_error"),
    )
    if user_agent:
        config["FunPay"]["user_agent"] = user_agent


def read_proxy(console, set_telebot_proxy=False, service="Telegram"):
    while True:
        value = console.read(console.text("proxy", service=service), secret=True)
        proxy = checked_proxy(value) if value else None
        if value and proxy is None:
            console.say("proxy_error")
            continue
        if set_telebot_proxy:
            telebot.apihelper.proxy = {"https": proxy, "http": proxy} if proxy else None
        return proxy


def checked_proxy(value):
    try:
        proxy = build_proxy(*validate_proxy(value))
        with requests.get(
            settings.PROXY_CHECK_URL,
            proxies={"http": proxy, "https": proxy},
            timeout=settings.NETWORK_TIMEOUT,
            allow_redirects=False,
            stream=True,
        ) as response:
            return proxy if response.status_code == settings.HTTP_OK else None
    except (ValueError, TypeError, requests.RequestException):
        return None


def bot_username(token):
    result = telebot.apihelper._make_request(
        token, "getMe", params={"timeout": settings.NETWORK_TIMEOUT}
    )
    return telebot.types.User.de_json(result).username


def check_bot(token, console, lookup):
    console.say("token_checking")
    try:
        username = lookup(token)
    except Exception as error:
        report_bot_error(console, error)
        return None
    if not valid_bot_username(username):
        console.say("username_error")
        return None
    return username


def retry_telegram(config, console):
    choice = console.choice("retry", ("1", "2", "3", "4"))
    if choice == "3":
        raise KeyboardInterrupt
    if choice == "2":
        config["Telegram"]["proxy"] = read_proxy(console, set_telebot_proxy=True) or ""
    return choice


def configure_telegram(config, console, lookup=bot_username):
    console.step(2, console.text("step_telegram"))
    console.say("botfather", name=PROJECT_NAME, username=settings.BOT_USERNAME_EXAMPLE)
    config["Telegram"]["proxy"] = read_proxy(console, set_telebot_proxy=True) or ""
    while True:
        token = console.validated(
            console.text("token"),
            valid_bot_token,
            console.text("token_format"),
            secret=True,
        )
        while True:
            username = check_bot(token, console, lookup)
            if username is not None:
                config["Telegram"].update({"token": token, "enabled": "1"})
                console.success("connected", username=username)
                return
            if retry_telegram(config, console) == "1":
                break


def configure_password(config, console):
    console.step(3, console.text("step_password"))
    while True:
        password = console.validated(
            console.text("password"),
            valid_password,
            console.text("password_error"),
            secret=True,
        )
        confirmation = console.read(console.text("password_confirm"), secret=True)
        if hmac.compare_digest(password.encode(), confirmation.encode()):
            config["Telegram"]["secretKeyHash"] = hash_password(password)
            return
        console.say("password_mismatch")


def configure_funpay_proxy(config, console):
    console.step(4, console.text("step_connection"))
    proxy = read_proxy(console, service="FunPay")
    if proxy:
        config["Proxy"].update({"proxy": proxy, "enable": "1", "check": "1"})
