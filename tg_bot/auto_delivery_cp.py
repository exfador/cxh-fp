from __future__ import annotations
import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from tg_bot import utils, keyboards as kb, CBT, MENU_CFG
from tg_bot.static_keyboards import CLEAR_STATE_BTN
from telebot.types import (
    InlineKeyboardMarkup as K,
    InlineKeyboardButton as B,
    Message,
    CallbackQuery,
)
from Utils import cardinal_tools
from locales.localizer import Localizer
import itertools
import random
import string
import logging
import os
import re

logger = logging.getLogger("TGBot")
localizer = Localizer()
_ = localizer.translate
from tg_bot.delivery_control.lots import DeliveryLotControls
from tg_bot.delivery_control.files import DeliveryFileControls
from tg_bot.delivery_control.products import DeliveryProductControls


class AutoDeliveryControlPanel(
    DeliveryLotControls, DeliveryFileControls, DeliveryProductControls
):
    def __init__(self, crd):
        self.crd = crd
        self.tg = self.crd.telegram
        self.bot = self.tg.bot
        self.filename_re = re.compile("[А-Яа-яЁёA-Za-z0-9_\\- ]+")
        self.tg.cbq_handler(
            self.open_ad_lots_list, lambda c: c.data.startswith(f"{CBT.AD_LOTS_LIST}:")
        )
        self.tg.cbq_handler(
            self.open_fp_lots_list, lambda c: c.data.startswith(f"{CBT.FP_LOTS_LIST}:")
        )
        self.tg.cbq_handler(
            self.act_add_lot_manually,
            lambda c: c.data.startswith(f"{CBT.ADD_AD_TO_LOT_MANUALLY}:"),
        )
        self.tg.msg_handler(
            self.add_lot_manually,
            func=lambda m: self.tg.check_state(
                m.chat.id, m.from_user.id, CBT.ADD_AD_TO_LOT_MANUALLY
            ),
        )
        self.tg.cbq_handler(
            self.open_gf_list,
            lambda c: c.data.startswith(f"{CBT.PRODUCTS_FILES_LIST}:"),
        )
        self.tg.cbq_handler(
            self.act_create_gf, lambda c: c.data == CBT.CREATE_PRODUCTS_FILE
        )
        self.tg.msg_handler(
            self.create_gf,
            func=lambda m: self.tg.check_state(
                m.chat.id, m.from_user.id, CBT.CREATE_PRODUCTS_FILE
            ),
        )
        self.tg.cbq_handler(
            self.open_edit_lot_cp, lambda c: c.data.startswith(f"{CBT.EDIT_AD_LOT}:")
        )
        self.tg.cbq_handler(
            self.act_edit_delivery_text,
            lambda c: c.data.startswith(f"{CBT.EDIT_LOT_DELIVERY_TEXT}:"),
        )
        self.tg.msg_handler(
            self.edit_delivery_text,
            func=lambda m: self.tg.check_state(
                m.chat.id, m.from_user.id, CBT.EDIT_LOT_DELIVERY_TEXT
            ),
        )
        self.tg.cbq_handler(
            self.act_link_gf, lambda c: c.data.startswith(f"{CBT.BIND_PRODUCTS_FILE}:")
        )
        self.tg.msg_handler(
            self.link_gf,
            func=lambda m: self.tg.check_state(
                m.chat.id, m.from_user.id, CBT.BIND_PRODUCTS_FILE
            ),
        )
        self.tg.cbq_handler(
            self.switch_lot_setting, lambda c: c.data.startswith("switch_lot:")
        )
        self.tg.cbq_handler(
            self.create_lot_delivery_test,
            lambda c: c.data.startswith("test_auto_delivery:"),
        )
        self.tg.cbq_handler(
            self.del_lot, lambda c: c.data.startswith(f"{CBT.DEL_AD_LOT}:")
        )
        self.tg.cbq_handler(
            self.add_ad_to_lot, lambda c: c.data.startswith(f"{CBT.ADD_AD_TO_LOT}:")
        )
        self.tg.cbq_handler(
            self.update_funpay_lots_list,
            lambda c: c.data.startswith("update_funpay_lots:"),
        )
        self.tg.cbq_handler(
            self.open_gf_settings,
            lambda c: c.data.startswith(f"{CBT.EDIT_PRODUCTS_FILE}:"),
        )
        self.tg.cbq_handler(
            self.act_add_products_to_file,
            lambda c: c.data.startswith(f"{CBT.ADD_PRODUCTS_TO_FILE}:"),
        )
        self.tg.msg_handler(
            self.add_products_to_file,
            func=lambda m: self.tg.check_state(
                m.chat.id, m.from_user.id, CBT.ADD_PRODUCTS_TO_FILE
            ),
        )
        self.tg.cbq_handler(
            self.send_products_file,
            lambda c: c.data.startswith("download_products_file:"),
        )
        self.tg.cbq_handler(
            self.ask_del_products_file,
            lambda c: c.data.startswith("del_products_file:"),
        )
        self.tg.cbq_handler(
            self.del_products_file,
            lambda c: c.data.startswith("confirm_del_products_file:"),
        )


from tg_bot.delivery_control.registration import init_auto_delivery_cp

BIND_TO_PRE_INIT = [init_auto_delivery_cp]
