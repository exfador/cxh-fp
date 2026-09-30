from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
from tg_bot import keyboards as kb, CBT
from telebot.types import (
    InlineKeyboardMarkup as K,
    InlineKeyboardButton as B,
    Message,
    CallbackQuery,
)
from Utils import cardinal_tools
import itertools
import os
import tg_bot.auto_delivery_cp as _module_state


class DeliveryProductControls:
    def add_products_to_file(self, m: Message):
        state = self.tg.get_state(m.chat.id, m.from_user.id)["data"]
        file_index, el_index, offset, prev_page = (
            state["file_index"],
            state["element_index"],
            state["offset"],
            state["previous_page"],
        )
        self.tg.clear_state(m.chat.id, m.from_user.id, True)
        files = [i for i in os.listdir("storage/products") if i.endswith(".txt")]
        if file_index > len(files) - 1:
            if prev_page == 0:
                update_btn = B(
                    _module_state._("gl_refresh"),
                    callback_data=f"{CBT.PRODUCTS_FILES_LIST}:0",
                )
            else:
                update_btn = B(
                    _module_state._("gl_back"),
                    callback_data=f"{CBT.EDIT_AD_LOT}:{el_index}:{offset}",
                )
            error_keyboard = K().add(update_btn)
            self.bot.reply_to(
                m,
                _module_state._("gf_not_found_err", file_index),
                reply_markup=error_keyboard,
            )
            return
        file_name = files[file_index]
        products = list(
            itertools.filterfalse(lambda el: not el, m.text.strip().split("\n"))
        )
        if prev_page == 0:
            back_btn = B(
                _module_state._("gl_back"),
                callback_data=f"{CBT.EDIT_PRODUCTS_FILE}:{file_index}:{offset}",
            )
        else:
            back_btn = B(
                _module_state._("gl_back"),
                callback_data=f"{CBT.EDIT_AD_LOT}:{el_index}:{offset}",
            )
        try_again_btn = B(
            _module_state._("gf_try_add_again"),
            callback_data=f"{CBT.ADD_PRODUCTS_TO_FILE}:{file_index}:{el_index}:{offset}:{prev_page}",
        )
        add_more_btn = B(
            _module_state._("gf_add_more"),
            callback_data=f"{CBT.ADD_PRODUCTS_TO_FILE}:{file_index}:{el_index}:{offset}:{prev_page}",
        )
        products_text = "\n".join(products)
        try:
            with cardinal_tools.get_products_file_lock(f"storage/products/{file_name}"):
                with open(f"storage/products/{file_name}", "a", encoding="utf-8") as f:
                    f.write("\n")
                    f.write(products_text)
        except:
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            keyboard = K().row(back_btn, try_again_btn)
            self.bot.reply_to(
                m, _module_state._("gf_add_goods_err"), reply_markup=keyboard
            )
            return
        _module_state.logger.info(
            _module_state._(
                "log_gf_new_goods",
                m.from_user.username,
                m.from_user.id,
                len(products),
                file_name,
            )
        )
        keyboard = K().row(back_btn, add_more_btn)
        self.bot.reply_to(
            m,
            _module_state._("gf_new_goods", len(products), file_name),
            reply_markup=keyboard,
        )

    def send_products_file(self, c: CallbackQuery):
        split = c.data.split(":")
        file_index, offset = (int(split[1]), int(split[2]))
        files = [i for i in os.listdir("storage/products") if i.endswith(".txt")]
        if not self.check_products_file_exists(
            file_index, files, c.message, reply_mode=False
        ):
            self.bot.answer_callback_query(c.id)
            return
        file_name = files[file_index]
        with cardinal_tools.get_products_file_lock(f"storage/products/{file_name}"):
            with open(f"storage/products/{file_name}", "r", encoding="utf-8") as f:
                data = f.read().strip()
                if not data:
                    self.bot.answer_callback_query(
                        c.id,
                        _module_state._("gf_empty_error", file_name),
                        show_alert=True,
                    )
                    return
                _module_state.logger.info(
                    _module_state._(
                        "log_gf_downloaded",
                        c.from_user.username,
                        c.from_user.id,
                        file_name,
                    )
                )
                f.seek(0)
                self.bot.send_document(c.message.chat.id, f)
                self.bot.answer_callback_query(c.id)

    def ask_del_products_file(self, c: CallbackQuery):
        split = c.data.split(":")
        file_index, offset = (int(split[1]), int(split[2]))
        files = [i for i in os.listdir("storage/products") if i.endswith(".txt")]
        if not self.check_products_file_exists(
            file_index, files, c.message, reply_mode=False
        ):
            self.bot.answer_callback_query(c.id)
            return
        self.bot.edit_message_reply_markup(
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.products_file_edit(file_index, offset, True),
        )
        self.bot.answer_callback_query(c.id)

    def del_products_file(self, c: CallbackQuery):
        split = c.data.split(":")
        file_index, offset = (int(split[1]), int(split[2]))
        files = [i for i in os.listdir("storage/products") if i.endswith(".txt")]
        if not self.check_products_file_exists(
            file_index, files, c.message, reply_mode=False
        ):
            self.tg.answer_callback_query(c.id)
            return
        file_name = files[file_index]
        delivery_objs = [
            i
            for i in self.crd.AD_CFG.sections()
            if self.crd.AD_CFG[i].get("productsFileName") == file_name
        ]
        if delivery_objs:
            keyboard = K().add(
                B(
                    _module_state._("gl_back"),
                    callback_data=f"{CBT.EDIT_PRODUCTS_FILE}:{file_index}:{offset}",
                )
            )
            self.bot.edit_message_text(
                _module_state._("gf_linked_err", file_name),
                c.message.chat.id,
                c.message.id,
                reply_markup=keyboard,
            )
            self.bot.answer_callback_query(c.id)
            return
        try:
            with cardinal_tools.get_products_file_lock(f"storage/products/{file_name}"):
                os.remove(f"storage/products/{file_name}")
            _module_state.logger.info(
                _module_state._(
                    "log_gf_deleted", c.from_user.username, c.from_user.id, file_name
                )
            )
            self.bot.edit_message_text(
                _module_state._("desc_gf"),
                c.message.chat.id,
                c.message.id,
                reply_markup=kb.products_files_list(offset),
            )
            self.bot.answer_callback_query(c.id)
        except:
            keyboard = K().add(
                B(
                    _module_state._("gl_back"),
                    callback_data=f"{CBT.EDIT_PRODUCTS_FILE}:{file_index}:{offset}",
                )
            )
            self.bot.edit_message_text(
                _module_state._("gf_deleting_err", file_name),
                c.message.chat.id,
                c.message.id,
                reply_markup=keyboard,
            )
            self.bot.answer_callback_query(c.id)
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            return
