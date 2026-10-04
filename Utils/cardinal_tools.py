from __future__ import annotations
from typing import TYPE_CHECKING
import bcrypt
import requests
from locales.localizer import Localizer
from Utils.products_storage import write_products

if TYPE_CHECKING:
    from cardinal import Cardinal
import FunPayAPI.types
from datetime import datetime
import Utils.exceptions
import itertools
import threading
import psutil
import json
import sys
import os
import re
import time
import logging

PHOTO_RE = re.compile("\\$photo=[\\d]+")
ENTITY_RE = re.compile("\\$photo=\\d+|\\$new|(\\$sleep=(\\d+\\.\\d+|\\d+))")
logger = logging.getLogger("FunPay CoxerHub.cardinal_tools")
localizer = Localizer()
_ = localizer.translate
_products_file_locks: dict[str, threading.Lock] = {}
_products_file_locks_guard = threading.Lock()


def get_products_file_lock(path: str) -> threading.Lock:
    normalized = os.path.normcase(os.path.abspath(path))
    with _products_file_locks_guard:
        if normalized not in _products_file_locks:
            _products_file_locks[normalized] = threading.Lock()
        return _products_file_locks[normalized]


def count_products(path: str) -> int:
    with get_products_file_lock(path):
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as f:
            products = f.read()
    products = products.split("\n")
    products = list(itertools.filterfalse(lambda el: not el, products))
    return len(products)


def cache_blacklist(blacklist: list[str]) -> None:
    from Utils.blacklist_store import write_blacklist

    write_blacklist(blacklist)


def load_blacklist() -> list[str]:
    if not os.path.exists("storage/cache/blacklist.json"):
        return []
    with open("storage/cache/blacklist.json", "r", encoding="utf-8") as f:
        blacklist = f.read()
        try:
            blacklist = json.loads(blacklist)
        except json.decoder.JSONDecodeError:
            return []
        return blacklist


def check_proxy(proxy: dict) -> bool:
    logger.info(_("crd_checking_proxy"))
    try:
        response = requests.get("https://api.ipify.org/", proxies=proxy, timeout=10)
    except:
        logger.error(_("crd_proxy_err"))
        logger.debug("TRACEBACK", exc_info=True)
        return False
    logger.info(_("crd_proxy_success", response.content.decode()))
    return True


def validate_proxy(proxy: str):
    if "://" in proxy:
        scheme, rest = proxy.split("://", 1)
    else:
        scheme = "http"
        rest = proxy
    if "@" in rest:
        login_password, ip_port = rest.split("@")
        login, password = login_password.split(":")
    else:
        login, password = ("", "")
        ip_port = rest
    ip, port = ip_port.split(":")
    ip_parts = ip.split(".")
    if len(ip_parts) != 4 or not all(
        (part.isdigit() and 0 <= int(part) < 256 for part in ip_parts)
    ):
        raise ValueError("Неправильный IP")
    if not port.isdigit() or not 0 < int(port) <= 65535:
        raise ValueError("Неправильный порт")
    if scheme not in ("http", "https", "socks5", "socks5h"):
        raise ValueError("Схема прокси должна быть http, https, socks5 или socks5h")
    return (scheme, login, password, ip, port)


def build_proxy(
    scheme: str | None, login: str, password: str, ip: str, port: str
) -> str:
    if not scheme:
        scheme = "http"
    if login and password:
        return f"{scheme}://{login}:{password}@{ip}:{port}"
    else:
        return f"{scheme}://{ip}:{port}"


def cache_proxy_dict(proxy_dict: dict[int, str]) -> None:
    if not os.path.exists("storage/cache"):
        os.makedirs("storage/cache")
    with open("storage/cache/proxy_dict.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(proxy_dict, indent=4))


def load_proxy_dict() -> dict[int, str]:
    if not os.path.exists("storage/cache/proxy_dict.json"):
        return {}
    with open("storage/cache/proxy_dict.json", "r", encoding="utf-8") as f:
        proxy = f.read()
        try:
            proxy = json.loads(proxy)
            proxy_dict = {}
            for id_, proxy_str in proxy.items():
                try:
                    proxy_dict[int(id_)] = build_proxy(*validate_proxy(proxy_str))
                except:
                    logger.debug(f"Не удалось добавить {proxy_str}")
                    logger.debug("TRACEBACK", exc_info=True)
        except json.decoder.JSONDecodeError:
            return {}
        return proxy_dict


def cache_disabled_plugins(disabled_plugins: list[str]) -> None:
    if not os.path.exists("storage/cache"):
        os.makedirs("storage/cache")
    with open("storage/cache/disabled_plugins.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(disabled_plugins))


def load_disabled_plugins() -> list[str]:
    if not os.path.exists("storage/cache/disabled_plugins.json"):
        return []
    with open("storage/cache/disabled_plugins.json", "r", encoding="utf-8") as f:
        try:
            return json.loads(f.read())
        except json.decoder.JSONDecodeError:
            return []


def cache_pinned_plugins(pinned_plugins: list[str]) -> None:
    if not os.path.exists("storage/cache"):
        os.makedirs("storage/cache")
    with open("storage/cache/pinned_plugins.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(pinned_plugins))


def load_pinned_plugins() -> list[str]:
    if not os.path.exists("storage/cache/pinned_plugins.json"):
        return []
    with open("storage/cache/pinned_plugins.json", "r", encoding="utf-8") as f:
        try:
            return json.loads(f.read())
        except json.decoder.JSONDecodeError:
            return []


def cache_old_users(old_users: dict[int, float]):
    if not os.path.exists("storage/cache"):
        os.makedirs("storage/cache")
    with open(f"storage/cache/old_users.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(old_users, ensure_ascii=False))


def load_old_users(greetings_cooldown: float) -> dict[int, float]:
    if not os.path.exists(f"storage/cache/old_users.json"):
        return dict()
    with open(f"storage/cache/old_users.json", "r", encoding="utf-8") as f:
        users = f.read()
    try:
        users = json.loads(users)
    except json.decoder.JSONDecodeError:
        return dict()
    if type(users) == list:
        users = {user: time.time() for user in users}
    else:
        users = {
            int(user): time_
            for user, time_ in users.items()
            if time.time() - time_ < greetings_cooldown * 24 * 60 * 60
        }
    cache_old_users(users)
    return users


def create_greeting_text(cardinal: Cardinal):
    from app.console_status import account_summary

    return account_summary(cardinal)


def time_to_str(time_: int, units=("д", "ч", "мин", "с")):
    days = time_ // 86400
    hours = (time_ - days * 86400) // 3600
    minutes = (time_ - days * 86400 - hours * 3600) // 60
    seconds = time_ - days * 86400 - hours * 3600 - minutes * 60
    if not any([days, hours, minutes, seconds]):
        return f"0 {units[3]}"
    parts = [
        f"{value} {unit}"
        for value, unit in zip((days, hours, minutes, seconds), units)
        if value
    ]
    return " ".join(parts)


def get_month_name(month_number: int) -> str:
    months = [
        "Января",
        "Февраля",
        "Марта",
        "Апреля",
        "Мая",
        "Июня",
        "Июля",
        "Августа",
        "Сентября",
        "Октября",
        "Ноября",
        "Декабря",
    ]
    if month_number > len(months):
        return months[0]
    return months[month_number - 1]


def get_products(path: str, amount: int = 1) -> list[list[str] | int] | None:
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
        raise ValueError("Product amount must be a positive integer")
    with get_products_file_lock(path):
        with open(path, "r", encoding="utf-8") as f:
            products = f.read()
        products = products.split("\n")
        products = list(itertools.filterfalse(lambda el: not el, products))
        if not products:
            raise Utils.exceptions.NoProductsError(path)
        elif len(products) < amount:
            raise Utils.exceptions.NotEnoughProductsError(path, len(products), amount)
        got_products = products[:amount]
        save_products = products[amount:]
        amount = len(save_products)
        write_products(path, "\n".join(save_products))
        return [got_products, amount]


def add_products(path: str, products: list[str], at_zero_position=False):
    with get_products_file_lock(path):
        text = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        elif at_zero_position:
            raise FileNotFoundError(path)
        content = "\n".join(products)
        write_products(
            path, content + "\n" + text if at_zero_position else text + "\n" + content
        )


def safe_text(text: str):
    return "\u2063".join(text)


def format_msg_text(
    text: str, obj: FunPayAPI.types.Message | FunPayAPI.types.ChatShortcut
) -> str:
    date_obj = datetime.now()
    month_name = get_month_name(date_obj.month)
    date = date_obj.strftime("%d.%m.%Y")
    str_date = f"{date_obj.day} {month_name}"
    str_full_date = str_date + f" {date_obj.year} года"
    time_ = date_obj.strftime("%H:%M")
    time_full = date_obj.strftime("%H:%M:%S")
    username = obj.author if isinstance(obj, FunPayAPI.types.Message) else obj.name
    chat_name = obj.chat_name if isinstance(obj, FunPayAPI.types.Message) else obj.name
    chat_id = (
        str(obj.chat_id) if isinstance(obj, FunPayAPI.types.Message) else str(obj.id)
    )
    variables = {
        "$full_date_text": str_full_date,
        "$date_text": str_date,
        "$date": date,
        "$time": time_,
        "$full_time": time_full,
        "$username": safe_text(username),
        "$message_text": str(obj),
        "$chat_id": chat_id,
        "$chat_name": safe_text(chat_name),
    }
    for var in variables:
        text = text.replace(var, variables[var])
    return text


def format_order_text(
    text: str, order: FunPayAPI.types.OrderShortcut | FunPayAPI.types.Order
) -> str:
    date_obj = datetime.now()
    month_name = get_month_name(date_obj.month)
    date = date_obj.strftime("%d.%m.%Y")
    str_date = f"{date_obj.day} {month_name}"
    str_full_date = str_date + f" {date_obj.year} года"
    time_ = date_obj.strftime("%H:%M")
    time_full = date_obj.strftime("%H:%M:%S")
    game = subcategory_fullname = subcategory = ""
    try:
        if isinstance(order, FunPayAPI.types.OrderShortcut) and (not order.subcategory):
            game, subcategory = order.subcategory_name.rsplit(", ", 1)
            subcategory_fullname = f"{subcategory} {game}"
        else:
            subcategory_fullname = order.subcategory.fullname
            game = order.subcategory.category.name
            subcategory = order.subcategory.name
    except:
        logger.warning("Произошла ошибка при парсинге игры из заказа")
        logger.debug("TRACEBACK", exc_info=True)
    description = (
        order.description
        if isinstance(order, FunPayAPI.types.OrderShortcut)
        else order.short_description
        if order.short_description
        else ""
    )
    params = (
        order.lot_params_text
        if isinstance(order, FunPayAPI.types.Order) and order.lot_params
        else ""
    )
    variables = {
        "$full_date_text": str_full_date,
        "$date_text": str_date,
        "$date": date,
        "$time": time_,
        "$full_time": time_full,
        "$username": safe_text(order.buyer_username),
        "$order_desc_and_params": f"{description}, {params}"
        if description and params
        else f"{description}{params}",
        "$order_desc_or_params": description if description else params,
        "$order_desc": description,
        "$order_title": description,
        "$order_params": params,
        "$order_id": order.id,
        "$order_link": f"https://funpay.com/orders/{order.id}/",
        "$category_fullname": subcategory_fullname,
        "$category": subcategory,
        "$game": game,
    }
    for var in variables:
        text = text.replace(var, variables[var])
    return text


def restart_program():
    from Utils.logger import stop_logging, configure_logging

    stop_logging()
    try:
        os.execl(sys.executable, sys.executable, *sys.argv)
    except OSError:
        configure_logging()
        raise


def shut_down():
    from Utils.logger import stop_logging

    stop_logging()
    os._exit(0)


def set_console_title(title: str) -> None:
    try:
        if os.name == "nt":
            import ctypes

            ctypes.windll.kernel32.SetConsoleTitleW(title)
    except:
        logger.warning("Произошла ошибка при изменении названия консоли")
        logger.debug("TRACEBACK", exc_info=True)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    return hashed_password.decode()


def check_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())
