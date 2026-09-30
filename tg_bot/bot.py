from __future__ import annotations
import re
from typing import TYPE_CHECKING
from FunPayAPI import Account
from tg_bot.utils import NotificationTypes
from tg_bot.constants.notification_policy import DISABLED_NOTIFICATION_TYPES
from tg_bot.constants.commands import PUBLIC_COMMANDS

if TYPE_CHECKING:
    from cardinal import Cardinal
import os
import sys
import time
import random
import string
import psutil
import telebot
from telebot.apihelper import ApiTelegramException
import logging
from telebot.types import (
    InlineKeyboardMarkup as K,
    InlineKeyboardButton as B,
    Message,
    CallbackQuery,
    BotCommand,
    InputFile,
)
from tg_bot import utils, static_keyboards as skb, keyboards as kb, CBT
from Utils import cardinal_tools, updater
from locales.localizer import Localizer

logger = logging.getLogger("CoxerHubBot.telegram")
localizer = Localizer()
_ = localizer.translate
telebot.apihelper.ENABLE_MIDDLEWARE = True
from tg_bot.control.session_access import SessionAccess
from tg_bot.control.account_admin import AccountAdministration
from tg_bot.control.system_settings import SystemSettings
from tg_bot.control.order_interface import OrderInterface
from tg_bot.control.routing_notifications import RoutingNotifications
from tg_bot.control.lot_pricing import LotPricing
from tg_bot.control.navigation import MenuNavigation
from tg_bot.control.menu_sections import MenuSections
from tg_bot.control.menu_trading import MenuTrading
from tg_bot.control.menu_input import MenuInput
from tg_bot.control.menu_service import MenuService
from tg_bot.control.operator_actions import OperatorActions
from tg_bot.control.blocklist import BlocklistPanel
from tg_bot.menu_sessions import MenuSessionStore
from threading import Lock
from tg_bot.premium_client import PremiumTeleBot
from tg_bot.panel_navigation import PanelNavigation
from tg_bot.control.updates import UpdatePanel


class TGBot(
    UpdatePanel,
    SessionAccess,
    AccountAdministration,
    SystemSettings,
    OrderInterface,
    RoutingNotifications,
    LotPricing,
    MenuNavigation,
    MenuSections,
    MenuTrading,
    MenuInput,
    MenuService,
    OperatorActions,
    BlocklistPanel,
):
    def __init__(self, cardinal: Cardinal):
        self.cardinal = cardinal
        if cardinal.MAIN_CFG["Telegram"]["proxy"]:
            telebot.apihelper.proxy = {
                "https": cardinal.MAIN_CFG["Telegram"]["proxy"],
                "http": cardinal.MAIN_CFG["Telegram"]["proxy"],
            }
        self.bot = PremiumTeleBot(
            self.cardinal.MAIN_CFG["Telegram"]["token"],
            parse_mode="HTML",
            allow_sending_without_reply=True,
            num_threads=5,
        )
        self.file_handlers = {}
        self.attempts = {}
        self.init_messages = []
        self.user_states = {}
        self.menu_store = MenuSessionStore()
        self.menu_backup_lock = Lock()
        self.process_action_lock = Lock()
        self.notification_settings = utils.load_notification_settings()
        self.answer_templates = utils.load_answer_templates()
        self.authorized_users = utils.load_authorized_users()
        self.commands = dict(PUBLIC_COMMANDS)
        self.__default_notification_settings = {}
        self.panel_navigation = PanelNavigation(self)
        self.bot.panel_navigation = self.panel_navigation
