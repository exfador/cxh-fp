from __future__ import annotations
from Utils.logging_support.constants.private_content import PRIVATE_SECRET_SUMMARY
from tg_bot.constants.message_defaults import DEFAULT_DELIVERY_RESPONSE
import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
from tg_bot import utils, keyboards as kb, CBT, MENU_CFG
from tg_bot.static_keyboards import CLEAR_STATE_BTN
from telebot.types import (
    InlineKeyboardMarkup as K,
    InlineKeyboardButton as B,
    Message,
    CallbackQuery,
)
from Utils import cardinal_tools
import random
import string
import os
import tg_bot.auto_delivery_cp as _module_state


class DeliveryFileControls:
    def link_gf(self, m: Message):
        user_state = self.tg.get_state(m.chat.id, m.from_user.id)
        lot_index, offset = (
            user_state["data"]["lot_index"],
            user_state["data"]["offset"],
        )
        self.tg.clear_state(m.chat.id, m.from_user.id, True)
        if not self.check_ad_lot_exists(lot_index, m):
            return
        lot = self.crd.AD_CFG.sections()[lot_index]
        lot_obj = self.crd.AD_CFG[lot]
        file_name = m.text.strip()
        exists = 1
        if "$product" not in lot_obj.get("response") and file_name != "-":
            keyboard = K().add(
                B(
                    _module_state._("gl_back"),
                    callback_data=f"{CBT.EDIT_AD_LOT}:{lot_index}:{offset}",
                )
            )
            self.bot.reply_to(
                m, _module_state._("ad_product_var_err2"), reply_markup=keyboard
            )
            return
        keyboard = K().row(
            B(
                _module_state._("gl_back"),
                callback_data=f"{CBT.EDIT_AD_LOT}:{lot_index}:{offset}",
            ),
            B(
                _module_state._("ea_link_another_gf"),
                callback_data=f"{CBT.BIND_PRODUCTS_FILE}:{lot_index}:{offset}",
            ),
        )
        if file_name == "-":
            self.crd.AD_CFG.remove_option(lot, "productsFileName")
            self.crd.save_config(self.crd.AD_CFG, "configs/auto_delivery.cfg")
            _module_state.logger.info(
                _module_state._(
                    "log_gf_unlinked", m.from_user.username, m.from_user.id, lot
                )
            )
            self.bot.reply_to(
                m,
                _module_state._("ad_gf_unlinked", utils.escape(lot)),
                reply_markup=keyboard,
            )
            return
        if not self.filename_re.fullmatch(file_name):
            error_keyboard = K().row(
                B(
                    _module_state._("gl_back"),
                    callback_data=f"{CBT.EDIT_AD_LOT}:{lot_index}:{offset}",
                ),
                B(
                    _module_state._("ea_link_another_gf"),
                    callback_data=f"{CBT.BIND_PRODUCTS_FILE}:{lot_index}:{offset}",
                ),
            )
            self.bot.reply_to(
                m, _module_state._("gf_name_invalid"), reply_markup=error_keyboard
            )
            return
        file_name += ".txt"
        if not os.path.exists(f"storage/products/{file_name}"):
            self.bot.send_message(
                m.chat.id, _module_state._("ad_creating_gf", file_name)
            )
            exists = 0
            try:
                with open(f"storage/products/{file_name}", "w", encoding="utf-8"):
                    pass
            except:
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                self.bot.reply_to(
                    m,
                    _module_state._("gf_creation_err", file_name),
                    reply_markup=keyboard,
                )
                return
        self.crd.AD_CFG.set(lot, "productsFileName", file_name)
        self.crd.save_config(self.crd.AD_CFG, "configs/auto_delivery.cfg")
        if exists:
            _module_state.logger.info(
                _module_state._(
                    "log_gf_linked",
                    m.from_user.username,
                    m.from_user.id,
                    file_name,
                    lot,
                )
            )
            self.bot.reply_to(
                m,
                _module_state._("ad_gf_linked", file_name, utils.escape(lot)),
                reply_markup=keyboard,
            )
        else:
            _module_state.logger.info(
                _module_state._(
                    "log_gf_created_and_linked",
                    m.from_user.username,
                    m.from_user.id,
                    file_name,
                    lot,
                )
            )
            self.bot.reply_to(
                m,
                _module_state._(
                    "ad_gf_created_and_linked", file_name, utils.escape(lot)
                ),
                reply_markup=keyboard,
            )

    def switch_lot_setting(self, c: CallbackQuery):
        split = c.data.split(":")
        param, lot_number, offset = (split[1], int(split[2]), int(split[3]))
        if not self.check_ad_lot_exists(lot_number, c.message, reply_mode=False):
            self.bot.answer_callback_query(c.id)
            return
        lot = self.crd.AD_CFG.sections()[lot_number]
        lot_obj = self.crd.AD_CFG[lot]
        value = str(int(not lot_obj.getboolean(param)))
        self.crd.AD_CFG.set(lot, param, value)
        self.crd.save_config(self.crd.AD_CFG, "configs/auto_delivery.cfg")
        _module_state.logger.info(
            _module_state._(
                "log_param_changed",
                c.from_user.username,
                c.from_user.id,
                param,
                lot,
                value,
            )
        )
        self.bot.edit_message_text(
            utils.generate_lot_info_text(lot_obj),
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.edit_lot(self.crd, lot_number, offset),
        )
        self.bot.answer_callback_query(c.id)

    def create_lot_delivery_test(self, c: CallbackQuery):
        split = c.data.split(":")
        lot_index, offset = (int(split[1]), int(split[2]))
        if not self.check_ad_lot_exists(lot_index, c.message, reply_mode=False):
            self.bot.answer_callback_query(c.id)
            return
        lot_name = self.crd.AD_CFG.sections()[lot_index]
        key = "".join(random.sample(string.ascii_letters + string.digits, 50))
        self.crd.delivery_tests[key] = lot_name
        _module_state.logger.info(
            _module_state._(
                "log_new_ad_key",
                c.from_user.username,
                c.from_user.id,
                lot_name,
                PRIVATE_SECRET_SUMMARY,
            )
        )
        keyboard = K().row(
            B(
                _module_state._("gl_back"),
                callback_data=f"{CBT.EDIT_AD_LOT}:{lot_index}:{offset}",
            ),
            B(
                _module_state._("ea_more_test"),
                callback_data=f"test_auto_delivery:{lot_index}:{offset}",
            ),
        )
        self.bot.send_message(
            c.message.chat.id,
            _module_state._("test_ad_key_created", utils.escape(lot_name), key),
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(c.id)

    def del_lot(self, c: CallbackQuery):
        split = c.data.split(":")
        lot_number, offset = (int(split[1]), int(split[2]))
        if not self.check_ad_lot_exists(lot_number, c.message, reply_mode=False):
            self.bot.answer_callback_query(c.id)
            return
        lot = self.crd.AD_CFG.sections()[lot_number]
        self.crd.AD_CFG.remove_section(lot)
        self.crd.save_config(self.crd.AD_CFG, "configs/auto_delivery.cfg")
        _module_state.logger.info(
            _module_state._("log_ad_deleted", c.from_user.username, c.from_user.id, lot)
        )
        self.bot.edit_message_text(
            _module_state._("desc_ad_list"),
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.lots_list(self.crd, offset),
        )
        self.bot.answer_callback_query(c.id)

    def update_funpay_lots_list(self, c: CallbackQuery):
        offset = int(c.data.split(":")[1])
        new_msg = self.bot.send_message(
            c.message.chat.id, _module_state._("ad_updating_lots_list")
        )
        self.bot.answer_callback_query(c.id)
        result = self.crd.update_lots_and_categories()
        if not result:
            self.bot.edit_message_text(
                _module_state._("ad_lots_list_updating_err"),
                new_msg.chat.id,
                new_msg.id,
            )
            return
        self.bot.delete_message(new_msg.chat.id, new_msg.id)
        c.data = f"{CBT.FP_LOTS_LIST}:{offset}"
        self.open_fp_lots_list(c)

    def add_ad_to_lot(self, c: CallbackQuery):
        split = c.data.split(":")
        fp_lot_index, fp_lots_offset = (int(split[1]), int(split[2]))
        if fp_lot_index > len(self.crd.tg_profile.get_common_lots()) - 1:
            update_button = K().add(
                B(_module_state._("gl_refresh"), callback_data=f"{CBT.FP_LOTS_LIST}:0")
            )
            self.bot.edit_message_text(
                _module_state._("ad_lot_not_found_err", fp_lot_index),
                c.message.chat.id,
                c.message.id,
                reply_markup=update_button,
            )
            self.bot.answer_callback_query(c.id)
            return
        lot = self.crd.tg_profile.get_common_lots()[fp_lot_index]
        if lot.title in self.crd.AD_CFG.sections():
            ad_lot_index = self.crd.AD_CFG.sections().index(lot.title)
            ad_lots_offset = ad_lot_index - 4 if ad_lot_index - 4 > 0 else 0
            keyboard = K().row(
                B(
                    _module_state._("gl_back"),
                    callback_data=f"{CBT.FP_LOTS_LIST}:{fp_lots_offset}",
                ),
                B(
                    _module_state._("gl_configure"),
                    callback_data=f"{CBT.EDIT_AD_LOT}:{ad_lot_index}:{ad_lots_offset}",
                ),
            )
            self.bot.send_message(
                c.message.chat.id,
                _module_state._("ad_already_ad_err", utils.escape(lot.title)),
                reply_markup=keyboard,
            )
            self.bot.answer_callback_query(c.id)
            return
        self.crd.AD_CFG.add_section(lot.title)
        self.crd.AD_CFG.set(
            lot.title,
            "response",
            DEFAULT_DELIVERY_RESPONSE,
        )
        self.crd.save_config(self.crd.AD_CFG, "configs/auto_delivery.cfg")
        ad_lot_index = len(self.crd.AD_CFG.sections()) - 1
        ad_lots_offset = utils.get_offset(ad_lot_index, MENU_CFG.AD_BTNS_AMOUNT)
        keyboard = K().row(
            B(
                _module_state._("gl_back"),
                callback_data=f"{CBT.FP_LOTS_LIST}:{fp_lots_offset}",
            ),
            B(
                _module_state._("gl_configure"),
                callback_data=f"{CBT.EDIT_AD_LOT}:{ad_lot_index}:{ad_lots_offset}",
            ),
        )
        _module_state.logger.info(
            _module_state._(
                "log_ad_linked", c.from_user.username, c.from_user.id, lot.title
            )
        )
        self.bot.send_message(
            c.message.chat.id,
            _module_state._("ad_lot_linked", utils.escape(lot.title)),
            reply_markup=keyboard,
        )
        self.bot.answer_callback_query(c.id)

    def open_gf_settings(self, c: CallbackQuery):
        split = c.data.split(":")
        file_index, offset = (int(split[1]), int(split[2]))
        files = [i for i in os.listdir("storage/products") if i.endswith(".txt")]
        if not self.check_products_file_exists(
            file_index, files, c.message, reply_mode=False
        ):
            self.bot.answer_callback_query(c.id)
            return
        file_name = files[file_index]
        products_amount = cardinal_tools.count_products(f"storage/products/{file_name}")
        nl = "\n"
        delivery_objs = [
            i
            for i in self.crd.AD_CFG.sections()
            if self.crd.AD_CFG[i].get("productsFileName") == file_name
        ]
        text = f"<b><u>{file_name}</u></b>\n\n<b><i>{_module_state._('gf_amount')}:</i></b>  <code>{products_amount}</code>\n\n<b><i>{_module_state._('gf_uses')}:</i></b>\n{nl.join((f'<code>{utils.escape(i)}</code>' for i in delivery_objs))}\n\n<i>{_module_state._('gl_last_update')}:</i>  <code>{datetime.datetime.now().strftime('%H:%M:%S')}</code>"
        self.bot.edit_message_text(
            text,
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.products_file_edit(file_index, offset),
        )
        self.bot.answer_callback_query(c.id)

    def act_add_products_to_file(self, c: CallbackQuery):
        split = c.data.split(":")
        file_index, el_index, offset, prev_page = (
            int(split[1]),
            int(split[2]),
            int(split[3]),
            int(split[4]),
        )
        result = self.bot.send_message(
            c.message.chat.id,
            _module_state._("gf_send_new_goods"),
            reply_markup=CLEAR_STATE_BTN(),
        )
        self.tg.set_state(
            c.message.chat.id,
            result.id,
            c.from_user.id,
            CBT.ADD_PRODUCTS_TO_FILE,
            {
                "file_index": file_index,
                "element_index": el_index,
                "offset": offset,
                "previous_page": prev_page,
            },
        )
        self.bot.answer_callback_query(c.id)
