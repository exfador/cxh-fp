from __future__ import annotations
from Utils.logging_support.private_content import private_content_summary
from Utils.logging_support.constants.private_content import PRIVATE_SECRET_SUMMARY
import re
from typing import TYPE_CHECKING
from FunPayAPI import Account

if TYPE_CHECKING:
    pass
import os
import time
import random
import string
from telebot.types import Message, CallbackQuery
from tg_bot import utils, static_keyboards as skb, CBT
from Utils import cardinal_tools
import tg_bot.bot as _module_state


class AccountAdministration:
    def change_cookie(self, m: Message):
        self.clear_state(m.chat.id, m.from_user.id, True)
        golden_key = m.text
        if (
            len(golden_key) != 32
            or golden_key != golden_key.lower()
            or len(golden_key.split()) != 1
        ):
            self.bot.send_message(m.chat.id, _module_state._("cookie_incorrect_format"))
            return
        self.bot.delete_message(m.chat.id, m.id)
        new_account = Account(
            golden_key,
            self.cardinal.account.user_agent,
            proxy=self.cardinal.proxy,
            locale=self.cardinal.account.locale,
        )
        try:
            new_account.get()
        except:
            _module_state.logger.warning("Произошла ошибка")
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            self.bot.send_message(m.chat.id, _module_state._("cookie_error"))
            return
        one_acc = False
        if (
            new_account.id == self.cardinal.account.id
            or self.cardinal.account.id is None
        ):
            one_acc = True
            self.cardinal.account.golden_key = golden_key
            try:
                self.cardinal.account.get()
            except:
                _module_state.logger.warning("Произошла ошибка")
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                self.bot.send_message(m.chat.id, _module_state._("cookie_error"))
                return
            accs = f" (<a href='https://funpay.com/users/{new_account.id}/'>{new_account.username}</a>)"
        else:
            accs = f" (<a href='https://funpay.com/users/{self.cardinal.account.id}/'>{self.cardinal.account.username}</a> ➔ <a href='https://funpay.com/users/{new_account.id}/'>{new_account.username}</a>)"
        self.cardinal.MAIN_CFG.set("FunPay", "golden_key", golden_key)
        self.cardinal.save_config(self.cardinal.MAIN_CFG, "configs/_main.cfg")
        self.bot.send_message(
            m.chat.id,
            f"{_module_state._('cookie_changed', accs)}{(_module_state._('cookie_changed2') if not one_acc else '')}",
            disable_web_page_preview=True,
        )

    def update_profile(self, c: CallbackQuery):
        new_msg = self.bot.send_message(
            c.message.chat.id, _module_state._("updating_profile")
        )
        try:
            self.cardinal.account.get()
            self.cardinal.balance = self.cardinal.get_balance()
        except:
            self.bot.edit_message_text(
                _module_state._("profile_updating_error"), new_msg.chat.id, new_msg.id
            )
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            self.bot.answer_callback_query(c.id)
            return
        self.bot.delete_message(new_msg.chat.id, new_msg.id)
        self.bot.edit_message_text(
            utils.generate_profile_text(self.cardinal),
            c.message.chat.id,
            c.message.id,
            reply_markup=skb.REFRESH_BTN(),
        )

    def act_manual_delivery_test(self, m: Message):
        result = self.bot.send_message(
            m.chat.id,
            _module_state._("create_test_ad_key"),
            reply_markup=skb.CLEAR_STATE_BTN(),
        )
        self.set_state(m.chat.id, result.id, m.from_user.id, CBT.MANUAL_AD_TEST)

    def manual_delivery_text(self, m: Message):
        self.clear_state(m.chat.id, m.from_user.id, True)
        lot_name = m.text.strip()
        key = "".join(random.sample(string.ascii_letters + string.digits, 50))
        self.cardinal.delivery_tests[key] = lot_name
        _module_state.logger.info(
            _module_state._(
                "log_new_ad_key",
                m.from_user.username,
                m.from_user.id,
                lot_name,
                PRIVATE_SECRET_SUMMARY,
            )
        )
        self.bot.send_message(
            m.chat.id,
            _module_state._("test_ad_key_created", utils.escape(lot_name), key),
        )

    def act_ban(self, m: Message):
        result = self.bot.send_message(
            m.chat.id,
            _module_state._("act_blacklist"),
            reply_markup=skb.CLEAR_STATE_BTN(),
        )
        self.set_state(m.chat.id, result.id, m.from_user.id, CBT.BAN)

    def ban(self, m: Message):
        self.clear_state(m.chat.id, m.from_user.id, True)
        nickname = m.text.strip()
        if nickname in self.cardinal.blacklist:
            self.bot.send_message(
                m.chat.id, _module_state._("already_blacklisted", nickname)
            )
            return
        self.cardinal.blacklist.append(nickname)
        cardinal_tools.cache_blacklist(self.cardinal.blacklist)
        _module_state.logger.info(
            _module_state._(
                "log_user_blacklisted", m.from_user.username, m.from_user.id, nickname
            )
        )
        self.bot.send_message(m.chat.id, _module_state._("user_blacklisted", nickname))

    def act_unban(self, m: Message):
        result = self.bot.send_message(
            m.chat.id, _module_state._("act_unban"), reply_markup=skb.CLEAR_STATE_BTN()
        )
        self.set_state(m.chat.id, result.id, m.from_user.id, CBT.UNBAN)

    def unban(self, m: Message):
        self.clear_state(m.chat.id, m.from_user.id, True)
        nickname = m.text.strip()
        if nickname not in self.cardinal.blacklist:
            self.bot.send_message(
                m.chat.id, _module_state._("not_blacklisted", nickname)
            )
            return
        self.cardinal.blacklist.remove(nickname)
        cardinal_tools.cache_blacklist(self.cardinal.blacklist)
        _module_state.logger.info(
            _module_state._(
                "log_user_unbanned", m.from_user.username, m.from_user.id, nickname
            )
        )
        self.bot.send_message(m.chat.id, _module_state._("user_unbanned", nickname))

    def send_ban_list(self, m: Message):
        if not self.cardinal.blacklist:
            self.bot.send_message(m.chat.id, _module_state._("blacklist_empty"))
            return
        blacklist = ", ".join(
            (
                f"<code>{i}</code>"
                for i in sorted(self.cardinal.blacklist, key=lambda x: x.lower())
            )
        )
        self.bot.send_message(m.chat.id, blacklist)

    def act_edit_watermark(self, m: Message):
        watermark = self.cardinal.MAIN_CFG["Other"]["watermark"]
        watermark = (
            f"\n<code>{utils.escape(watermark)}</code>"
            if watermark
            else f" {_module_state._('watermark_none')}"
        )
        result = self.bot.send_message(
            m.chat.id,
            _module_state._("act_edit_watermark").format(watermark),
            reply_markup=skb.CLEAR_STATE_BTN(),
        )
        self.set_state(m.chat.id, result.id, m.from_user.id, CBT.EDIT_WATERMARK)

    def edit_watermark(self, m: Message):
        watermark = m.text if m.text != "-" else ""
        if re.fullmatch("\\[[a-zA-Z]+]", watermark):
            self.bot.reply_to(m, _module_state._("watermark_error"))
            return
        self.save_watermark(watermark)
        self.clear_state(m.chat.id, m.from_user.id)
        if watermark:
            _module_state.logger.info(
                _module_state._(
                    "log_watermark_changed",
                    m.from_user.username,
                    m.from_user.id,
                    private_content_summary(watermark),
                )
            )
            self.bot.reply_to(m, _module_state._("watermark_changed", watermark))
        else:
            _module_state.logger.info(
                _module_state._(
                    "log_watermark_deleted", m.from_user.username, m.from_user.id
                )
            )
            self.bot.reply_to(m, _module_state._("watermark_deleted"))

    def save_watermark(self, watermark):
        previous = self.cardinal.MAIN_CFG["Other"]["watermark"]
        self.cardinal.MAIN_CFG["Other"]["watermark"] = watermark
        try:
            self.cardinal.save_config(self.cardinal.MAIN_CFG, "configs/_main.cfg")
        except OSError:
            self.cardinal.MAIN_CFG["Other"]["watermark"] = previous
            raise

    def send_logs(self, m: Message):
        from tg_bot.control.log_files import send_logs

        send_logs(self, m)

    def del_logs(self, m: Message):
        from tg_bot.control.log_files import clear_logs

        clear_logs(self, m)

    def about(self, m: Message):
        self.bot.send_message(
            m.chat.id, _module_state._("about", self.cardinal.VERSION)
        )
