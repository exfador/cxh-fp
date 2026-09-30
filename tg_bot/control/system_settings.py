from __future__ import annotations
from Utils.logging_support.private_content import private_content_summary
from tg_bot.constants.process_controls import (
    SHUTDOWN_CONFIRMATION_STATE,
    SHUTDOWN_CONFIRMATION_SECONDS,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
import os
import time
import psutil
from telebot.types import (
    InlineKeyboardMarkup as K,
    InlineKeyboardButton as B,
    Message,
    CallbackQuery,
    InputFile,
)
from tg_bot import static_keyboards as skb, keyboards as kb, CBT
from Utils import cardinal_tools, updater
import tg_bot.bot as _module_state


class SystemSettings:
    def get_backup(self, m: Message):
        from tg_bot.control.backup_files import send_backup

        send_backup(self, m)

    def create_backup(self, m: Message):
        if updater.create_backup():
            self.bot.send_message(m.chat.id, _module_state._("update_backup_error"))
            return False
        self.get_backup(m)
        return True

    def send_system_info(self, m: Message):
        current_time = int(time.time())
        uptime = current_time - self.cardinal.start_time
        ram = psutil.virtual_memory()
        cpu_usage = "\n".join(
            (
                f"    CPU {i}:  <code>{l}%</code>"
                for i, l in enumerate(psutil.cpu_percent(percpu=True))
            )
        )
        self.bot.send_message(
            m.chat.id,
            _module_state._(
                "sys_info",
                cpu_usage,
                psutil.Process().cpu_percent(),
                ram.total // 1048576,
                ram.used // 1048576,
                ram.free // 1048576,
                psutil.Process().memory_info().rss // 1048576,
                cardinal_tools.time_to_str(uptime),
                m.chat.id,
            ),
        )

    def restart_cardinal(self, m: Message):
        self.bot.send_message(m.chat.id, _module_state._("restarting"))
        cardinal_tools.restart_program()

    def ask_power_off(self, m: Message):
        if not self.menu_user_allowed(m.from_user, m.chat):
            return
        sent = self.bot.send_message(
            m.chat.id,
            _module_state._("power_off_0"),
            reply_markup=kb.power_off(self.cardinal.instance_id, 0),
        )
        self.set_state(
            m.chat.id,
            sent.id,
            m.from_user.id,
            CBT.SHUT_DOWN,
            {"instance": self.cardinal.instance_id, "created": time.monotonic()},
        )

    def cancel_power_off(self, c: CallbackQuery):
        if not c.message or not self.menu_user_allowed(c.from_user, c.message.chat):
            return
        self.clear_state(c.message.chat.id, c.from_user.id)
        self.bot.edit_message_text(
            _module_state._("power_off_cancelled"), c.message.chat.id, c.message.id
        )
        self.bot.answer_callback_query(c.id)

    def power_off(self, c: CallbackQuery):
        if not c.message or not self.menu_user_allowed(c.from_user, c.message.chat):
            return
        with self.process_action_lock:
            if not self.shutdown_request_valid(c):
                self.bot.answer_callback_query(c.id, _module_state._("power_off_error"))
                return
            self.clear_state(c.message.chat.id, c.from_user.id)
            self.bot.edit_message_text(
                _module_state._("power_off_6"), c.message.chat.id, c.message.id
            )
            self.bot.answer_callback_query(c.id)
            cardinal_tools.shut_down()

    def shutdown_request_valid(self, call):
        state = self.get_state(call.message.chat.id, call.from_user.id)
        if state is None or state["state"] != CBT.SHUT_DOWN:
            return False
        expected = (
            f"{CBT.SHUT_DOWN}:{SHUTDOWN_CONFIRMATION_STATE}:{self.cardinal.instance_id}"
        )
        return (
            call.data == expected
            and state["mid"] == call.message.id
            and state["data"]["instance"] == self.cardinal.instance_id
            and time.monotonic() - state["data"]["created"]
            < SHUTDOWN_CONFIRMATION_SECONDS
        )

    def act_send_funpay_message(self, c: CallbackQuery):
        split = c.data.split(":")
        node_id = int(split[1])
        try:
            username = split[2]
        except IndexError:
            username = None
        result = self.bot.send_message(
            c.message.chat.id,
            _module_state._("enter_msg_text"),
            reply_markup=skb.CLEAR_STATE_BTN(),
        )
        self.set_state(
            c.message.chat.id,
            result.id,
            c.from_user.id,
            CBT.SEND_FP_MESSAGE,
            {"node_id": node_id, "username": username},
        )
        self.bot.answer_callback_query(c.id)

    def send_funpay_message(self, message: Message):
        data = self.get_state(message.chat.id, message.from_user.id)["data"]
        node_id, username = (data["node_id"], data["username"])
        self.clear_state(message.chat.id, message.from_user.id, True)
        response_text = message.text.strip()
        result = self.cardinal.send_message(
            node_id, response_text, username, watermark=False
        )
        if result:
            self.bot.reply_to(
                message,
                _module_state._("msg_sent", node_id, username),
                reply_markup=kb.reply(node_id, username, again=True, extend=True),
            )
        else:
            self.bot.reply_to(
                message,
                _module_state._("msg_sending_error", node_id, username),
                reply_markup=kb.reply(node_id, username, again=True, extend=True),
            )

    def act_upload_image(self, m: Message):
        cbt = (
            CBT.UPLOAD_CHAT_IMAGE
            if m.text.startswith("/upload_chat_img")
            else CBT.UPLOAD_OFFER_IMAGE
        )
        result = self.bot.send_message(
            m.chat.id, _module_state._("send_img"), reply_markup=skb.CLEAR_STATE_BTN()
        )
        self.set_state(m.chat.id, result.id, m.from_user.id, cbt)

    def act_upload_backup(self, m: Message):
        result = self.bot.send_message(
            m.chat.id,
            _module_state._("send_backup"),
            reply_markup=skb.CLEAR_STATE_BTN(),
        )
        self.set_state(m.chat.id, result.id, m.from_user.id, CBT.UPLOAD_BACKUP)

    def act_edit_greetings_text(self, c: CallbackQuery):
        variables = [
            "v_date",
            "v_date_text",
            "v_full_date_text",
            "v_time",
            "v_full_time",
            "v_username",
            "v_message_text",
            "v_chat_id",
            "v_chat_name",
            "v_photo",
            "v_sleep",
        ]
        text = (
            f"{_module_state._('v_edit_greeting_text')}\n\n{_module_state._('v_list')}:\n"
            + "\n".join((_module_state._(i) for i in variables))
        )
        result = self.bot.send_message(
            c.message.chat.id, text, reply_markup=skb.CLEAR_STATE_BTN()
        )
        self.set_state(
            c.message.chat.id, result.id, c.from_user.id, CBT.EDIT_GREETINGS_TEXT
        )
        self.bot.answer_callback_query(c.id)

    def edit_greetings_text(self, m: Message):
        self.clear_state(m.chat.id, m.from_user.id, True)
        self.cardinal.MAIN_CFG["Greetings"]["greetingsText"] = m.text
        _module_state.logger.info(
            _module_state._(
                "log_greeting_changed",
                m.from_user.username,
                m.from_user.id,
                private_content_summary(m.text),
            )
        )
        self.cardinal.save_config(self.cardinal.MAIN_CFG, "configs/_main.cfg")
        keyboard = K().row(
            B(_module_state._("gl_back"), callback_data=f"{CBT.CATEGORY}:gr"),
            B(_module_state._("gl_edit"), callback_data=CBT.EDIT_GREETINGS_TEXT),
        )
        self.bot.reply_to(m, _module_state._("greeting_changed"), reply_markup=keyboard)

    def act_edit_greetings_cooldown(self, c: CallbackQuery):
        text = _module_state._("v_edit_greeting_cooldown")
        result = self.bot.send_message(
            c.message.chat.id, text, reply_markup=skb.CLEAR_STATE_BTN()
        )
        self.set_state(
            c.message.chat.id, result.id, c.from_user.id, CBT.EDIT_GREETINGS_COOLDOWN
        )
        self.bot.answer_callback_query(c.id)

    def edit_greetings_cooldown(self, m: Message):
        self.clear_state(m.chat.id, m.from_user.id, True)
        try:
            cooldown = float(m.text)
        except:
            self.bot.reply_to(m, _module_state._("gl_error_try_again"))
            return
        self.cardinal.MAIN_CFG["Greetings"]["greetingsCooldown"] = str(cooldown)
        _module_state.logger.info(
            _module_state._(
                "log_greeting_cooldown_changed",
                m.from_user.username,
                m.from_user.id,
                m.text,
            )
        )
        self.cardinal.save_config(self.cardinal.MAIN_CFG, "configs/_main.cfg")
        keyboard = K().row(
            B(_module_state._("gl_back"), callback_data=f"{CBT.CATEGORY}:gr"),
            B(_module_state._("gl_edit"), callback_data=CBT.EDIT_GREETINGS_COOLDOWN),
        )
        self.bot.reply_to(
            m,
            _module_state._("greeting_cooldown_changed").format(m.text),
            reply_markup=keyboard,
        )

    def act_edit_order_confirm_reply_text(self, c: CallbackQuery):
        variables = [
            "v_date",
            "v_date_text",
            "v_full_date_text",
            "v_time",
            "v_full_time",
            "v_username",
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
            f"{_module_state._('v_edit_order_confirm_text')}\n\n{_module_state._('v_list')}:\n"
            + "\n".join((_module_state._(i) for i in variables))
        )
        result = self.bot.send_message(
            c.message.chat.id, text, reply_markup=skb.CLEAR_STATE_BTN()
        )
        self.set_state(
            c.message.chat.id,
            result.id,
            c.from_user.id,
            CBT.EDIT_ORDER_CONFIRM_REPLY_TEXT,
        )
        self.bot.answer_callback_query(c.id)

    def edit_order_confirm_reply_text(self, m: Message):
        self.clear_state(m.chat.id, m.from_user.id, True)
        self.cardinal.MAIN_CFG["OrderConfirm"]["replyText"] = m.text
        _module_state.logger.info(
            _module_state._(
                "log_order_confirm_changed",
                m.from_user.username,
                m.from_user.id,
                private_content_summary(m.text),
            )
        )
        self.cardinal.save_config(self.cardinal.MAIN_CFG, "configs/_main.cfg")
        keyboard = K().row(
            B(_module_state._("gl_back"), callback_data=f"{CBT.CATEGORY}:oc"),
            B(
                _module_state._("gl_edit"),
                callback_data=CBT.EDIT_ORDER_CONFIRM_REPLY_TEXT,
            ),
        )
        self.bot.reply_to(
            m, _module_state._("order_confirm_changed"), reply_markup=keyboard
        )

    def act_edit_review_reply_text(self, c: CallbackQuery):
        stars = int(c.data.split(":")[1])
        variables = [
            "v_date",
            "v_date_text",
            "v_full_date_text",
            "v_time",
            "v_full_time",
            "v_username",
            "v_order_id",
            "v_order_link",
            "v_order_title",
            "v_order_params",
            "v_order_desc_and_params",
            "v_order_desc_or_params",
            "v_game",
            "v_category",
            "v_category_fullname",
        ]
        text = (
            f"{_module_state._('v_edit_review_reply_text', '⭐' * stars)}\n\n{_module_state._('v_list')}:\n"
            + "\n".join((_module_state._(i) for i in variables))
        )
        result = self.bot.send_message(
            c.message.chat.id, text, reply_markup=skb.CLEAR_STATE_BTN()
        )
        self.set_state(
            c.message.chat.id,
            result.id,
            c.from_user.id,
            CBT.EDIT_REVIEW_REPLY_TEXT,
            {"stars": stars},
        )
        self.bot.answer_callback_query(c.id)

    def edit_review_reply_text(self, m: Message):
        stars = self.get_state(m.chat.id, m.from_user.id)["data"]["stars"]
        self.clear_state(m.chat.id, m.from_user.id, True)
        self.cardinal.MAIN_CFG["ReviewReply"][f"star{stars}ReplyText"] = m.text
        _module_state.logger.info(
            _module_state._(
                "log_review_reply_changed",
                m.from_user.username,
                m.from_user.id,
                stars,
                private_content_summary(m.text),
            )
        )
        self.cardinal.save_config(self.cardinal.MAIN_CFG, "configs/_main.cfg")
        keyboard = K().row(
            B(_module_state._("gl_back"), callback_data=f"{CBT.CATEGORY}:rr"),
            B(
                _module_state._("gl_edit"),
                callback_data=f"{CBT.EDIT_REVIEW_REPLY_TEXT}:{stars}",
            ),
        )
        self.bot.reply_to(
            m,
            _module_state._("review_reply_changed", "⭐" * stars),
            reply_markup=keyboard,
        )

    def open_reply_menu(self, c: CallbackQuery):
        split = c.data.split(":")
        node_id, username, again = (int(split[1]), split[2], int(split[3]))
        extend = True if len(split) > 4 and int(split[4]) else False
        self.bot.edit_message_reply_markup(
            c.message.chat.id,
            c.message.id,
            reply_markup=kb.reply(node_id, username, bool(again), extend),
        )
