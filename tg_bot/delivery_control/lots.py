from __future__ import annotations
from Utils.logging_support.private_content import private_content_summary
from tg_bot.constants.message_defaults import DEFAULT_DELIVERY_RESPONSE
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
import os
import tg_bot.auto_delivery_cp as _module_state


class DeliveryLotControls:
    def check_ad_lot_exists(
        self, index: int, message_obj: Message, reply_mode: bool = True
    ) -> bool:
        if index > len(self.crd.AD_CFG.sections()) - 1:
            update_button = K().add(
                B(_module_state._("gl_refresh"), callback_data=f"{CBT.AD_LOTS_LIST}:0")
            )
            if reply_mode:
                self.bot.reply_to(
                    message_obj,
                    _module_state._("ad_lot_not_found_err", index),
                    reply_markup=update_button,
                )
            else:
                self.bot.edit_message_text(
                    _module_state._("ad_lot_not_found_err", index),
                    message_obj.chat.id,
                    message_obj.id,
                    reply_markup=update_button,
                )
            return False
        return True

    def check_products_file_exists(
        self,
        index: int,
        files_list: list[str],
        message_obj: Message,
        reply_mode: bool = True,
    ) -> bool:
        if index > len(files_list) - 1:
            update_button = K().add(
                B(
                    _module_state._("gl_refresh"),
                    callback_data=f"{CBT.PRODUCTS_FILES_LIST}:0",
                )
            )
            if reply_mode:
                self.bot.reply_to(
                    message_obj,
                    _module_state._("gf_not_found_err", index),
                    reply_markup=update_button,
                )
            else:
                self.bot.edit_message_text(
                    _module_state._("gf_not_found_err", index),
                    message_obj.chat.id,
                    message_obj.id,
                    reply_markup=update_button,
                )
            return False
        return True

    def open_ad_lots_list(self, c: CallbackQuery):
        offset = int(c.data.split(":")[1])
        self.bot.edit_message_text(
            _module_state._("desc_ad_list"),
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.lots_list(self.crd, offset),
        )
        self.bot.answer_callback_query(c.id)

    def open_fp_lots_list(self, c: CallbackQuery):
        offset = int(c.data.split(":")[1])
        self.bot.edit_message_text(
            _module_state._(
                "desc_ad_fp_lot_list",
                self.crd.last_telegram_lots_update.strftime("%d.%m.%Y %H:%M:%S"),
            ),
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.funpay_lots_list(self.crd, offset),
        )
        self.bot.answer_callback_query(c.id)

    def act_add_lot_manually(self, c: CallbackQuery):
        offset = int(c.data.split(":")[1])
        result = self.bot.send_message(
            c.message.chat.id,
            _module_state._("copy_lot_name"),
            reply_markup=CLEAR_STATE_BTN(),
        )
        self.tg.set_state(
            c.message.chat.id,
            result.id,
            c.from_user.id,
            CBT.ADD_AD_TO_LOT_MANUALLY,
            data={"offset": offset},
        )
        self.bot.answer_callback_query(c.id)

    def add_lot_manually(self, m: Message):
        fp_lots_offset = self.tg.get_state(m.chat.id, m.from_user.id)["data"]["offset"]
        self.tg.clear_state(m.chat.id, m.from_user.id, True)
        lot = m.text.strip()
        if lot in self.crd.AD_CFG.sections():
            error_keyboard = K().row(
                B(
                    _module_state._("gl_back"),
                    callback_data=f"{CBT.FP_LOTS_LIST}:{fp_lots_offset}",
                ),
                B(
                    _module_state._("ad_add_another_ad"),
                    callback_data=f"{CBT.ADD_AD_TO_LOT_MANUALLY}:{fp_lots_offset}",
                ),
            )
            self.bot.reply_to(
                m,
                _module_state._("ad_lot_already_exists", utils.escape(lot)),
                reply_markup=error_keyboard,
            )
            return
        self.crd.AD_CFG.add_section(lot)
        self.crd.AD_CFG.set(
            lot,
            "response",
            DEFAULT_DELIVERY_RESPONSE,
        )
        self.crd.save_config(self.crd.AD_CFG, "configs/auto_delivery.cfg")
        _module_state.logger.info(
            _module_state._("log_ad_linked", m.from_user.username, m.from_user.id, lot)
        )
        lot_index = len(self.crd.AD_CFG.sections()) - 1
        ad_lot_offset = utils.get_offset(lot_index, MENU_CFG.AD_BTNS_AMOUNT)
        keyboard = K().row(
            B(
                _module_state._("gl_back"),
                callback_data=f"{CBT.FP_LOTS_LIST}:{fp_lots_offset}",
            ),
            B(
                _module_state._("ad_add_more_ad"),
                callback_data=f"{CBT.ADD_AD_TO_LOT_MANUALLY}:{fp_lots_offset}",
            ),
            B(
                _module_state._("gl_configure"),
                callback_data=f"{CBT.EDIT_AD_LOT}:{lot_index}:{ad_lot_offset}",
            ),
        )
        self.bot.send_message(
            m.chat.id, _module_state._("ad_lot_linked", lot), reply_markup=keyboard
        )

    def open_gf_list(self, c: CallbackQuery):
        offset = int(c.data.split(":")[1])
        self.bot.edit_message_text(
            _module_state._("desc_gf"),
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.products_files_list(offset),
        )
        self.bot.answer_callback_query(c.id)

    def act_create_gf(self, c: CallbackQuery):
        result = self.bot.send_message(
            c.message.chat.id,
            _module_state._("act_create_gf"),
            reply_markup=CLEAR_STATE_BTN(),
        )
        self.tg.set_state(
            c.message.chat.id, result.id, c.from_user.id, CBT.CREATE_PRODUCTS_FILE
        )
        self.bot.answer_callback_query(c.id)

    def create_gf(self, m: Message):
        self.tg.clear_state(m.chat.id, m.from_user.id, True)
        file_name = m.text.strip()
        error_keyboard = K().row(
            B(_module_state._("gl_back"), callback_data=f"{CBT.CATEGORY}:ad"),
            B(
                _module_state._("gf_create_another"),
                callback_data=CBT.CREATE_PRODUCTS_FILE,
            ),
        )
        if not self.filename_re.fullmatch(file_name):
            self.bot.reply_to(
                m, _module_state._("gf_name_invalid"), reply_markup=error_keyboard
            )
            return
        file_name += ".txt"
        if os.path.exists(f"storage/products/{file_name}"):
            file_index = os.listdir("storage/products").index(file_name)
            offset = file_index - 4 if file_index - 4 > 0 else 0
            keyboard = K().row(
                B(_module_state._("gl_back"), callback_data=f"{CBT.CATEGORY}:ad"),
                B(
                    _module_state._("gf_create_another"),
                    callback_data=CBT.CREATE_PRODUCTS_FILE,
                ),
                B(
                    _module_state._("gl_configure"),
                    callback_data=f"{CBT.EDIT_PRODUCTS_FILE}:{file_index}:{offset}",
                ),
            )
            self.bot.reply_to(
                m,
                _module_state._("gf_already_exists_err", file_name),
                reply_markup=keyboard,
            )
            return
        try:
            with open(f"storage/products/{file_name}", "w", encoding="utf-8"):
                pass
        except:
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            self.bot.reply_to(
                m,
                _module_state._("gf_creation_err", file_name),
                reply_markup=error_keyboard,
            )
        file_index = os.listdir("storage/products").index(file_name)
        offset = file_index - 4 if file_index - 4 > 0 else 0
        keyboard = K().row(
            B(_module_state._("gl_back"), callback_data=f"{CBT.CATEGORY}:ad"),
            B(
                _module_state._("gf_create_more"),
                callback_data=CBT.CREATE_PRODUCTS_FILE,
            ),
            B(
                _module_state._("gl_configure"),
                callback_data=f"{CBT.EDIT_PRODUCTS_FILE}:{file_index}:{offset}",
            ),
        )
        _module_state.logger.info(
            _module_state._(
                "log_gf_created", m.from_user.username, m.from_user.id, file_name
            )
        )
        self.bot.send_message(
            m.chat.id, _module_state._("gf_created", file_name), reply_markup=keyboard
        )

    def open_edit_lot_cp(self, c: CallbackQuery):
        split = c.data.split(":")
        lot_index, offset = (int(split[1]), int(split[2]))
        if not self.check_ad_lot_exists(lot_index, c.message, reply_mode=False):
            self.bot.answer_callback_query(c.id)
            return
        lot = self.crd.AD_CFG.sections()[lot_index]
        lot_obj = self.crd.AD_CFG[lot]
        self.bot.edit_message_text(
            utils.generate_lot_info_text(lot_obj),
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.edit_lot(self.crd, lot_index, offset),
        )
        self.bot.answer_callback_query(c.id)

    def act_edit_delivery_text(self, c: CallbackQuery):
        split = c.data.split(":")
        lot_index, offset = (int(split[1]), int(split[2]))
        variables = [
            "v_date",
            "v_date_text",
            "v_full_date_text",
            "v_time",
            "v_full_time",
            "v_username",
            "v_product",
            "v_order_id",
            "v_order_link",
            "v_order_title",
            "v_game",
            "v_category",
            "v_category_fullname",
            "v_photo",
            "v_sleep",
        ]
        text = (
            f"{_module_state._('v_edit_delivery_text')}\n\n{_module_state._('v_list')}:\n"
            + "\n".join((_module_state._(i) for i in variables))
        )
        result = self.bot.send_message(
            c.message.chat.id, text, reply_markup=CLEAR_STATE_BTN()
        )
        self.tg.set_state(
            c.message.chat.id,
            result.id,
            c.from_user.id,
            CBT.EDIT_LOT_DELIVERY_TEXT,
            {"lot_index": lot_index, "offset": offset},
        )
        self.bot.answer_callback_query(c.id)

    def edit_delivery_text(self, m: Message):
        user_state = self.tg.get_state(m.chat.id, m.from_user.id)
        lot_index, offset = (
            user_state["data"]["lot_index"],
            user_state["data"]["offset"],
        )
        self.tg.clear_state(m.chat.id, m.from_user.id, True)
        if not self.check_ad_lot_exists(lot_index, m):
            return
        new_response = m.text.strip()
        lot = self.crd.AD_CFG.sections()[lot_index]
        lot_obj = self.crd.AD_CFG[lot]
        keyboard = K().row(
            B(
                _module_state._("gl_back"),
                callback_data=f"{CBT.EDIT_AD_LOT}:{lot_index}:{offset}",
            ),
            B(
                _module_state._("gl_edit"),
                callback_data=f"{CBT.EDIT_LOT_DELIVERY_TEXT}:{lot_index}:{offset}",
            ),
        )
        if (
            lot_obj.get("productsFileName") is not None
            and "$product" not in new_response
        ):
            self.bot.reply_to(
                m,
                _module_state._("ad_product_var_err", utils.escape(lot)),
                reply_markup=keyboard,
            )
            return
        self.crd.AD_CFG.set(lot, "response", new_response)
        self.crd.save_config(self.crd.AD_CFG, "configs/auto_delivery.cfg")
        _module_state.logger.info(
            _module_state._(
                "log_ad_text_changed",
                m.from_user.username,
                m.from_user.id,
                lot,
                private_content_summary(new_response),
            )
        )
        self.bot.reply_to(
            m,
            _module_state._(
                "ad_text_changed", utils.escape(lot), utils.escape(new_response)
            ),
            reply_markup=keyboard,
        )

    def act_link_gf(self, c: CallbackQuery):
        split = c.data.split(":")
        lot_index, offset = (int(split[1]), int(split[2]))
        result = self.bot.send_message(
            c.message.chat.id,
            _module_state._("ad_link_gf"),
            reply_markup=CLEAR_STATE_BTN(),
        )
        self.tg.set_state(
            c.message.chat.id,
            result.id,
            c.from_user.id,
            CBT.BIND_PRODUCTS_FILE,
            {"lot_index": lot_index, "offset": offset},
        )
        self.bot.answer_callback_query(c.id)
