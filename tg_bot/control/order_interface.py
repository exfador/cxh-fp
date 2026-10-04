from __future__ import annotations
from contextlib import nullcontext
from app.constants.languages import SUPPORTED_LANGUAGES
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
import time
from telebot.types import (
    InlineKeyboardMarkup as K,
    InlineKeyboardButton as B,
    CallbackQuery,
)
from tg_bot import utils, static_keyboards as skb, keyboards as kb, CBT
from locales.localizer import Localizer
import tg_bot.bot as _module_state


class OrderInterface:
    def extend_new_message_notification(self, c: CallbackQuery):
        chat_id, username = c.data.split(":")[1:]
        try:
            chat = self.cardinal.account.get_chat(utils.parse_chat_id(chat_id))
        except:
            self.bot.answer_callback_query(c.id)
            self.bot.send_message(c.message.chat.id, _module_state._("get_chat_error"))
            return
        text = ""
        if chat.looking_link:
            text += f'''<b><i>{_module_state._("viewing")}:</i></b>\n<a href="{chat.looking_link}">{chat.looking_text}</a>\n\n'''
        text += utils.format_messages(self.cardinal, chat.messages[-10:])
        self.bot.edit_message_text(
            text,
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.reply(utils.parse_chat_id(chat_id), username, False, False),
        )

    def ask_confirm_refund(self, call: CallbackQuery):
        split = call.data.split(":")
        order_id, node_id, username = (
            split[1],
            utils.parse_chat_id(split[2]),
            split[3],
        )
        keyboard = kb.new_order(order_id, username, node_id, confirmation=True)
        self.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.id, reply_markup=keyboard
        )
        self.bot.answer_callback_query(call.id)

    def cancel_refund(self, call: CallbackQuery):
        split = call.data.split(":")
        order_id, node_id, username = (
            split[1],
            utils.parse_chat_id(split[2]),
            split[3],
        )
        keyboard = kb.new_order(order_id, username, node_id)
        self.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.id, reply_markup=keyboard
        )
        self.bot.answer_callback_query(call.id)

    def refund(self, c: CallbackQuery):
        split = c.data.split(":")
        order_id, node_id, username = (
            split[1],
            utils.parse_chat_id(split[2]),
            split[3],
        )
        new_msg = None
        attempts = 3
        while attempts:
            try:
                self.cardinal.account.refund(order_id)
                break
            except:
                if not new_msg:
                    new_msg = self.bot.send_message(
                        c.message.chat.id,
                        _module_state._("refund_attempt", order_id, attempts),
                    )
                else:
                    self.bot.edit_message_text(
                        _module_state._("refund_attempt", order_id, attempts),
                        new_msg.chat.id,
                        new_msg.id,
                    )
                attempts -= 1
                time.sleep(1)
        else:
            self.bot.edit_message_text(
                _module_state._("refund_error", order_id), new_msg.chat.id, new_msg.id
            )
            keyboard = kb.new_order(order_id, username, node_id)
            self.bot.edit_message_reply_markup(
                c.message.chat.id, c.message.id, reply_markup=keyboard
            )
            self.bot.answer_callback_query(c.id)
            return
        if not new_msg:
            self.bot.send_message(
                c.message.chat.id, _module_state._("refund_complete", order_id)
            )
        else:
            self.bot.edit_message_text(
                _module_state._("refund_complete", order_id),
                new_msg.chat.id,
                new_msg.id,
            )
        keyboard = kb.new_order(order_id, username, node_id, no_refund=True)
        self.bot.edit_message_reply_markup(
            c.message.chat.id, c.message.id, reply_markup=keyboard
        )
        self.bot.answer_callback_query(c.id)

    def open_order_menu(self, c: CallbackQuery):
        split = c.data.split(":")
        node_id, username, order_id, no_refund = (
            utils.parse_chat_id(split[1]),
            split[2],
            split[3],
            bool(int(split[4])),
        )
        self.bot.edit_message_reply_markup(
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.new_order(order_id, username, node_id, no_refund=no_refund),
        )

    def open_cp(self, c: CallbackQuery):
        self.open_home_menu(c)

    def open_cp2(self, c: CallbackQuery):
        self.open_more_settings(c)

    def switch_param(self, c: CallbackQuery):
        split = c.data.split(":")
        section, option = (split[1], split[2])
        if section == "FunPay" and option == "oldMsgGetMode":
            self.cardinal.switch_msg_get_mode()
        else:
            self.cardinal.MAIN_CFG[section][option] = str(
                int(not int(self.cardinal.MAIN_CFG[section][option]))
            )
            self.cardinal.save_config(self.cardinal.MAIN_CFG, "configs/_main.cfg")
        sections = {
            "FunPay": kb.main_settings,
            "BlockList": kb.blacklist_settings,
            "NewMessageView": kb.new_message_view_settings,
            "Greetings": kb.greeting_settings,
            "OrderConfirm": kb.order_confirm_reply_settings,
            "ReviewReply": kb.review_reply_settings,
        }
        if section == "Telegram":
            self.bot.edit_message_reply_markup(
                c.message.chat.id,
                c.message.id,
                reply_markup=kb.authorized_users(self.cardinal, offset=int(split[3])),
            )
        else:
            self.bot.edit_message_reply_markup(
                c.message.chat.id,
                c.message.id,
                reply_markup=sections[section](self.cardinal),
            )
        _module_state.logger.info(
            _module_state._(
                "log_param_changed",
                c.from_user.username,
                c.from_user.id,
                option,
                section,
                self.cardinal.MAIN_CFG[section][option],
            )
        )
        self.bot.answer_callback_query(c.id)

    def switch_chat_notification(self, c: CallbackQuery):
        if not c.message or not self.menu_user_allowed(c.from_user, c.message.chat):
            self.bot.answer_callback_query(c.id)
            return
        split = c.data.split(":")
        chat_id, notification_type = (int(split[1]), split[2])
        if chat_id != c.from_user.id:
            self.bot.answer_callback_query(c.id)
            return
        result = self.toggle_notification(chat_id, notification_type)
        _module_state.logger.info(
            _module_state._(
                "log_notification_switched",
                c.from_user.username,
                c.from_user.id,
                notification_type,
                c.message.chat.id,
                result,
            )
        )
        keyboard = kb.notifications_settings
        self.bot.edit_message_reply_markup(
            c.message.chat.id,
            c.message.id,
            reply_markup=keyboard(self.cardinal, c.message.chat.id),
        )
        self.bot.answer_callback_query(c.id)

    def open_settings_section(self, c: CallbackQuery):
        section = c.data.split(":")[1]
        sections = {
            "lang": (
                _module_state._("desc_lang"),
                kb.language_settings,
                [self.cardinal],
            ),
            "main": (_module_state._("desc_gs"), kb.main_settings, [self.cardinal]),
            "tg": (
                _module_state._("desc_ns", c.message.chat.id),
                kb.notifications_settings,
                [self.cardinal, c.message.chat.id],
            ),
            "bl": (_module_state._("desc_bl"), kb.blacklist_settings, [self.cardinal]),
            "ar": (_module_state._("desc_ar"), skb.AR_SETTINGS, []),
            "ad": (_module_state._("desc_ad"), skb.AD_SETTINGS, []),
            "mv": (
                _module_state._("desc_mv"),
                kb.new_message_view_settings,
                [self.cardinal],
            ),
            "rr": (
                _module_state._("desc_or"),
                kb.review_reply_settings,
                [self.cardinal],
            ),
            "gr": (
                _module_state._(
                    "desc_gr",
                    utils.escape(self.cardinal.MAIN_CFG["Greetings"]["greetingsText"]),
                ),
                kb.greeting_settings,
                [self.cardinal],
            ),
            "oc": (
                _module_state._(
                    "desc_oc",
                    utils.escape(self.cardinal.MAIN_CFG["OrderConfirm"]["replyText"]),
                ),
                kb.order_confirm_reply_settings,
                [self.cardinal],
            ),
        }
        curr = sections[section]
        self.bot.edit_message_text(
            curr[0], c.message.chat.id, c.message.id, reply_markup=curr[1](*curr[2])
        )
        self.bot.answer_callback_query(c.id)

    def cancel_action(self, call: CallbackQuery):
        navigation = getattr(self, "panel_navigation", None)
        with navigation.activate(None) if navigation else nullcontext():
            result = self.clear_state(call.message.chat.id, call.from_user.id, True)
        if navigation is not None and result is not None:
            navigation.history.forget(call.from_user.id, call.message.chat.id, result)
        if result is None:
            self.bot.answer_callback_query(call.id)

    def param_disabled(self, c: CallbackQuery):
        self.bot.answer_callback_query(
            c.id, _module_state._("param_disabled"), show_alert=True
        )

    def send_review_reply_text(self, c: CallbackQuery):
        stars = int(c.data.split(":")[1])
        text = self.cardinal.MAIN_CFG["ReviewReply"][f"star{stars}ReplyText"]
        keyboard = K().row(
            B(_module_state._("gl_back"), callback_data=f"{CBT.CATEGORY}:rr"),
            B(
                _module_state._("gl_edit"),
                callback_data=f"{CBT.EDIT_REVIEW_REPLY_TEXT}:{stars}",
            ),
        )
        if not text:
            self.bot.send_message(
                c.message.chat.id,
                _module_state._("review_reply_empty", "⭐" * stars),
                reply_markup=keyboard,
            )
        else:
            self.bot.send_message(
                c.message.chat.id,
                _module_state._(
                    "review_reply_text",
                    "⭐" * stars,
                    self.cardinal.MAIN_CFG["ReviewReply"][f"star{stars}ReplyText"],
                ),
                reply_markup=keyboard,
            )
        self.bot.answer_callback_query(c.id)

    def send_old_mode_help_text(self, c: CallbackQuery):
        self.bot.answer_callback_query(c.id)
        self.bot.send_message(c.message.chat.id, _module_state._("old_mode_help"))

    def empty_callback(self, c: CallbackQuery):
        self.bot.answer_callback_query(c.id)

    def switch_lang(self, c: CallbackQuery):
        if not c.message or not self.menu_user_allowed(c.from_user, c.message.chat):
            return
        lang = c.data.split(":")[1]
        if lang not in SUPPORTED_LANGUAGES:
            self.bot.answer_callback_query(
                c.id, _module_state._("language_unavailable")
            )
            return
        Localizer(lang)
        self.cardinal.MAIN_CFG["Other"]["language"] = lang
        self.cardinal.save_config(self.cardinal.MAIN_CFG, "configs/_main.cfg")
        c.data = f"{CBT.CATEGORY}:lang"
        self.open_settings_section(c)
