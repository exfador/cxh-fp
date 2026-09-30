from __future__ import annotations
import random
import re
import time
import uuid
from typing import TYPE_CHECKING, Generator
import requests

if TYPE_CHECKING:
    from ..account import Account
import json
import logging
from bs4 import BeautifulSoup
from ..common import exceptions
from ..common.utils import strip_invisible_suffix
from .events import *

logger = logging.getLogger("FunPayAPI.runner")
from FunPayAPI.updater.processing.requests import RequestProcessing
from FunPayAPI.updater.processing.chat_events import ChatEventProcessing
from FunPayAPI.updater.processing.order_events import OrderEventProcessing


class Runner(RequestProcessing, ChatEventProcessing, OrderEventProcessing):
    def __init__(
        self,
        account: Account,
        disable_message_requests: bool = False,
        disabled_order_requests: bool = False,
    ):
        if not account.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        if account.runner:
            raise Exception("К аккаунту уже привязан Runner!")
        self.make_msg_requests: bool = False if disable_message_requests else True
        self.make_order_requests: bool = False if disabled_order_requests else True
        self.__first_request = True
        self.__last_msg_event_tag = utils.random_tag()
        self.__last_order_event_tag = utils.random_tag()
        self.__is_running = False
        self.saved_orders: dict[str, types.OrderShortcut] | None = None
        self.runner_last_messages: dict[int, list[int, int, str | None]] = {}
        self.by_bot_ids: dict[int, list[int]] = {}
        self.last_messages_ids: dict[int, int] = {}
        self.chat_node_tags: dict[int, str] = {}
        self.users_ids: dict[int, int] = {}
        self.buyers_viewing: dict[int, types.BuyerViewing] = {}
        self.runner_len: int = 10
        self.payload_queue: dict[str, dict] = {}
        self.runner_results: dict[str, requests.Response | Exception] = {}
        self.account: Account = account
        self.__orders_counters: dict | None = None
        self.__chat_bookmarks: list[dict] = []
        self.__chat_nodes: dict[int, tuple[dict, int]] = {}
        self.__chat_bookmarks_time = 0
        self.account.runner = self
