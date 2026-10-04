from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from FunPayAPI import types
from FunPayAPI.common.enums import SubCategoryTypes
from Utils.cardinal_tools import validate_proxy, build_proxy
from Utils.text_encoding_normalizer import TextEncodingNormalizer

if TYPE_CHECKING:
    from configparser import ConfigParser
from tg_bot import (
    auto_response_cp,
    config_loader_cp,
    auto_delivery_cp,
    templates_cp,
    plugins_cp,
    file_uploader,
    authorized_users_cp,
    proxy_cp,
    default_cp,
)
from types import ModuleType
import Utils.exceptions
from uuid import UUID
import importlib.util
import configparser
import itertools
import requests
import datetime
import logging
import random
import time
import sys
import os
import FunPayAPI
import handlers
from cardinal_core import announcements
from locales.localizer import Localizer
from FunPayAPI import utils as fp_utils
from Utils import cardinal_tools
import tg_bot.bot
from threading import Thread

sys.modules.setdefault("announcements", announcements)
logger = logging.getLogger("FunPay CoxerHub")
localizer = Localizer()
_ = localizer.translate
from cardinal_core.plugin_data import get_cardinal, PluginData
from cardinal_core.plugin_compat import pip_main as main
from cardinal_core.raise_schedule import load_raise_schedule
from cardinal_core.account_operations import AccountOperations
from cardinal_core.messaging_runtime import MessagingRuntime
from cardinal_core.plugin_lifecycle import PluginLifecycle
from cardinal_core.plugin_hotswap import PluginHotSwap
from cardinal_core.feature_flags import FeatureFlags


class Cardinal(
    AccountOperations,
    MessagingRuntime,
    PluginLifecycle,
    PluginHotSwap,
    FeatureFlags,
    object,
):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(Cardinal, cls).__new__(cls)
        return getattr(cls, "instance")

    def __init__(
        self,
        main_config: ConfigParser,
        auto_delivery_config: ConfigParser,
        auto_response_config: ConfigParser,
        raw_auto_response_config: ConfigParser,
        version: str,
    ):
        self.VERSION = version
        self.instance_id = random.randint(0, 999999999)
        self.delivery_tests = {}
        self.MAIN_CFG = main_config
        self.AD_CFG = auto_delivery_config
        self.AR_CFG = auto_response_config
        self.RAW_AR_CFG = raw_auto_response_config
        self.proxy = {}
        self.proxy_dict = cardinal_tools.load_proxy_dict()
        if self.MAIN_CFG["Proxy"].getboolean("enable"):
            if self.MAIN_CFG["Proxy"]["proxy"]:
                logger.info(_("crd_proxy_detected"))
                scheme, login, password, ip, port = validate_proxy(
                    self.MAIN_CFG["Proxy"]["proxy"]
                )
                proxy_str = build_proxy(scheme, login, password, ip, port)
                self.proxy = {"http": proxy_str, "https": proxy_str}
                if proxy_str not in self.proxy_dict.values():
                    max_id = max(self.proxy_dict.keys(), default=-1)
                    self.proxy_dict[max_id + 1] = proxy_str
                    cardinal_tools.cache_proxy_dict(self.proxy_dict)
                if self.MAIN_CFG["Proxy"].getboolean("check") and (
                    not cardinal_tools.check_proxy(self.proxy)
                ):
                    sys.exit()
        self.account = FunPayAPI.Account(
            self.MAIN_CFG["FunPay"]["golden_key"],
            self.MAIN_CFG["FunPay"]["user_agent"],
            proxy=self.proxy,
        )
        self.runner: FunPayAPI.Runner | None = None
        self.telegram: tg_bot.bot.TGBot | None = None
        self.running = False
        self.run_id = 0
        self.start_time = int(time.time())
        self.balance: FunPayAPI.types.Balance | None = None
        self.raise_time, self.raised_time = load_raise_schedule()
        self.__exchange_rates = {}
        self.profile: FunPayAPI.types.UserProfile | None = None
        self.tg_profile: FunPayAPI.types.UserProfile | None = None
        self.last_tg_profile_update = datetime.datetime.now()
        self.curr_profile: FunPayAPI.types.UserProfile | None = None
        self.curr_profile_last_tag: str | None = None
        self.profile_last_tag: str | None = None
        self.last_state_change_tag: str | None = None
        self.last_profile_refresh_event_tag: str | None = None
        self.last_greeting_chat_id_threshold_change_tag: str | None = None
        self.greeting_threshold_chat_ids = set()
        self.blacklist = cardinal_tools.load_blacklist()
        self.old_users = cardinal_tools.load_old_users(
            float(self.MAIN_CFG["Greetings"]["greetingsCooldown"])
        )
        self.greeting_chat_id_threshold = max(self.old_users.keys(), default=0)
        self.pre_init_handlers = []
        self.post_init_handlers = []
        self.pre_start_handlers = []
        self.post_start_handlers = []
        self.pre_stop_handlers = []
        self.post_stop_handlers = []
        self.init_message_handlers = []
        self.messages_list_changed_handlers = []
        self.last_chat_message_changed_handlers = []
        self.new_message_handlers = []
        self.init_order_handlers = []
        self.orders_list_changed_handlers = []
        self.new_order_handlers = []
        self.order_status_changed_handlers = []
        self.pre_delivery_handlers = []
        self.post_delivery_handlers = []
        self.pre_lots_raise_handlers = []
        self.post_lots_raise_handlers = []
        self.handler_bind_var_names = {
            "BIND_TO_PRE_INIT": self.pre_init_handlers,
            "BIND_TO_POST_INIT": self.post_init_handlers,
            "BIND_TO_PRE_START": self.pre_start_handlers,
            "BIND_TO_POST_START": self.post_start_handlers,
            "BIND_TO_PRE_STOP": self.pre_stop_handlers,
            "BIND_TO_POST_STOP": self.post_stop_handlers,
            "BIND_TO_INIT_MESSAGE": self.init_message_handlers,
            "BIND_TO_MESSAGES_LIST_CHANGED": self.messages_list_changed_handlers,
            "BIND_TO_LAST_CHAT_MESSAGE_CHANGED": self.last_chat_message_changed_handlers,
            "BIND_TO_NEW_MESSAGE": self.new_message_handlers,
            "BIND_TO_INIT_ORDER": self.init_order_handlers,
            "BIND_TO_NEW_ORDER": self.new_order_handlers,
            "BIND_TO_ORDERS_LIST_CHANGED": self.orders_list_changed_handlers,
            "BIND_TO_ORDER_STATUS_CHANGED": self.order_status_changed_handlers,
            "BIND_TO_PRE_DELIVERY": self.pre_delivery_handlers,
            "BIND_TO_POST_DELIVERY": self.post_delivery_handlers,
            "BIND_TO_PRE_LOTS_RAISE": self.pre_lots_raise_handlers,
            "BIND_TO_POST_LOTS_RAISE": self.post_lots_raise_handlers,
        }
        self.plugins: dict[str, PluginData] = {}
        self.broken_plugins = {}
        self.disabled_plugins = cardinal_tools.load_disabled_plugins()
        self.pinned_plugins = cardinal_tools.load_pinned_plugins()
