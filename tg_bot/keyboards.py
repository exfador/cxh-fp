from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from telebot.types import InlineKeyboardMarkup as K, InlineKeyboardButton as B
from tg_bot import CBT, MENU_CFG
from tg_bot.utils import NotificationTypes, bool_to_text, add_navigation_buttons
import Utils
from locales.localizer import Localizer
import logging
import random
import os

logger = logging.getLogger("TGBot")
localizer = Localizer()
_ = localizer.translate
from tg_bot.keyboard_views.settings import (
    power_off,
    language_settings,
    main_settings,
    new_message_view_settings,
    greeting_settings,
    order_confirm_reply_settings,
    authorized_users,
    authorized_user_settings,
    proxy,
    review_reply_settings,
    notifications_settings,
    blacklist_settings,
    commands_list,
    edit_command,
)
from tg_bot.keyboard_views.messages import (
    products_files_list,
    products_file_edit,
    lots_list,
    funpay_lots_list,
    edit_lot,
    new_order,
    reply,
    templates_list,
    edit_template,
    templates_list_ans_mode,
    plugins_list,
    edit_plugin,
)
