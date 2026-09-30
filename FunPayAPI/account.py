from __future__ import annotations
import html
from typing import TYPE_CHECKING, Literal, Any, Optional, IO
import FunPayAPI.common.enums
from FunPayAPI.common.utils import (
    parse_currency,
    RegularExpressions,
    strip_invisible_suffix,
)
from .types import PaymentMethod, CalcResult

if TYPE_CHECKING:
    from .updater.runner import Runner
from requests_toolbelt import MultipartEncoder
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
import logging
import random
import string
import json
import time
import re
from FunPayAPI.security.request_policy import create_http_adapter
from . import types
from .common import exceptions, utils, enums

logger = logging.getLogger("FunPayAPI.account")
PRIVATE_CHAT_ID_RE = re.compile("users-\\d+-\\d+$")
from FunPayAPI.accounts.transport import RequestTransport
from FunPayAPI.accounts.catalog_queries import CatalogQueries
from FunPayAPI.accounts.chat_io import ChatOperations
from FunPayAPI.accounts.transactions import Transactions
from FunPayAPI.accounts.orders import OrderQueries
from FunPayAPI.accounts.offers_and_chats import OfferChatQueries
from FunPayAPI.accounts.profile_catalog import ProfileCatalog
from FunPayAPI.accounts.chat_parsing import ChatParser
from FunPayAPI.accounts.order_parsing import OrderParser


class Account(
    RequestTransport,
    CatalogQueries,
    ChatOperations,
    Transactions,
    OrderQueries,
    OfferChatQueries,
    ProfileCatalog,
    ChatParser,
    OrderParser,
):
    def __init__(
        self,
        golden_key: str,
        user_agent: str | None = None,
        requests_timeout: int | float = 10,
        proxy: Optional[dict] = None,
        locale: Literal["ru", "en", "uk"] | None = None,
    ):
        self.golden_key: str = golden_key
        self.user_agent: str | None = user_agent
        self.requests_timeout: int | float = requests_timeout
        self.proxy = proxy
        self.html: str | None = None
        self.app_data: dict | None = None
        self.id: int | None = None
        self.username: str | None = None
        self.active_sales: int | None = None
        self.active_purchases: int | None = None
        self.last_429_err_time: float = 0
        self.last_flood_err_time: float = 0
        self.last_multiuser_flood_err_time: float = 0
        self.__locale: Literal["ru", "en", "uk"] | None = None
        self.__default_locale: Literal["ru", "en", "uk"] | None = locale
        self.__profile_parse_locale: Literal["ru", "en", "uk"] | None = locale
        self.__chat_parse_locale: Literal["ru", "en", "uk"] | None = None
        self.__order_parse_locale: Literal["ru", "en", "uk"] | None = None
        self.__lots_parse_locale: Literal["ru", "en", "uk"] | None = None
        self.__subcategories_parse_locale: Literal["ru", "en", "uk"] | None = None
        self.__set_locale: Literal["ru", "en", "uk"] | None = None
        self.currency: FunPayAPI.types.Currency = FunPayAPI.types.Currency.UNKNOWN
        self.total_balance: int | None = None
        self.csrf_token: str | None = None
        self.phpsessid: str | None = None
        self.last_update: int | None = None
        self.__initiated: bool = False
        self.__saved_chats: dict[int, types.ChatShortcut] = {}
        self.runner: Runner | None = None
        self._logout_link: str | None = None
        self.__categories: list[types.Category] = []
        self.__sorted_categories: dict[int, types.Category] = {}
        self.__subcategories: list[types.SubCategory] = []
        self.__sorted_subcategories: dict[
            types.SubCategoryTypes, dict[int, types.SubCategory]
        ] = {types.SubCategoryTypes.COMMON: {}, types.SubCategoryTypes.CURRENCY: {}}
        self.__bot_character = "\u2061"
        self.__old_bot_character = "\u2064"
        self.session = requests.Session()
        self.session.trust_env = False
        self.cookies = {}
        self.session.mount("https://", create_http_adapter())
