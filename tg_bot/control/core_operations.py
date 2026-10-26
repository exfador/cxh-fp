import io
import logging
import time
from html import escape
from threading import Thread

from telebot.types import (
    InlineKeyboardButton as Button,
    InlineKeyboardMarkup as Keyboard,
)
from app.updates.store import load_state
from cardinal_core.order_journal import journal
from cardinal_core.native_stock import receipt_products
from tg_bot.core_operations import (
    text,
    summary,
    pending_rows,
    delivery_text,
    plugin_report,
    plugin_rows,
    preference_path,
)
from cardinal_core.withdraw_quote import CRYPTO, build_quote
from tg_bot.constants.menu import FUNPAY_BALANCE_URL, MENU_INPUT_STATE
from tg_bot.keyboard_views.menu import menu_back
from tg_bot.rate_watch import alerts_enabled, remember_rate, set_alerts
from tg_bot.withdraw_view import money, withdraw_text

WITHDRAW_CACHE_SECONDS = 60
WITHDRAW_REFRESH_SECONDS = 20


def button(token, action, label, argument="-"):
    return Button(label, callback_data=f"hub:{token}:{action}:{argument}")


def withdraw_keyboard(token, alerts=False, custom=False):
    keyboard = Keyboard().row(
        button(token, "withdraw", text("💰 Весь баланс", "💰 Whole balance"))
        if custom
        else button(token, "withdraw", text("↻ Обновить", "↻ Refresh"), "refresh")
    )
    keyboard.row(
        button(
            token,
            "withdraw_amount",
            text("✍️ Другая сумма", "✍️ Another amount")
            if custom
            else text("✍️ Своя сумма", "✍️ Custom amount"),
        )
    )
    label = (
        text("🔔 Уведомления о падении курса: вкл", "🔔 Rate drop alerts: on")
        if alerts
        else text("🔕 Уведомления о падении курса: выкл", "🔕 Rate drop alerts: off")
    )
    keyboard.row(button(token, "rate_alerts", label, "off" if alerts else "on"))
    keyboard.row(
        Button(
            text("🌐 Открыть вывод на FunPay", "🌐 Open FunPay payouts"),
            url=FUNPAY_BALANCE_URL,
        )
    )
    return menu_back(keyboard, token, "profile")


class CoreOperations:
    def menu_attention(self, call, token, argument):
        rows = pending_rows(self.cardinal)
        content = text(
            "🔎 <b>Требуют внимания</b>", "🔎 <b>Needs attention</b>"
        ) + summary(self.cardinal)
        content += text(
            "\n\nОткрытые заказы FunPay доступны в «Заказах». Статус выдачи плагинов проверяйте в их панелях.",
            "\n\nOpen FunPay orders are in Orders. Check plugin delivery in its own panel.",
        )
        page = max(
            0,
            min(
                int(argument) if str(argument).isdecimal() else 0,
                max(0, (len(rows) - 1) // 8),
            ),
        )
        keyboard = Keyboard()
        for row in rows[page * 8 : page * 8 + 8]:
            keyboard.row(button(token, "native_order", "📦 #" + row["id"], row["id"]))
        if page:
            keyboard.row(button(token, "attention", "‹", str(page - 1)))
        if len(rows) > (page + 1) * 8:
            keyboard.row(button(token, "attention", "›", str(page + 1)))
        keyboard.row(
            button(
                token,
                "plugin_health",
                text("🧩 Диагностика плагинов", "🧩 Plugin diagnostics"),
            )
        )
        keyboard.row(button(token, "attention", text("↻ Обновить", "↻ Refresh")))
        keyboard.row(
            button(token, "shop_check", text("🩺 Проверить магазин", "🩺 Check shop"))
        )
        self.menu_render(call, content, menu_back(keyboard, token))

    def native_row(self, identifier):
        row = journal(self.cardinal).read(identifier)
        if not row.get("native"):
            raise ValueError("No core delivery for this seller")
        return row

    def menu_native_order(self, call, token, argument):
        self.native_row(argument)
        keyboard = Keyboard().row(
            Button(
                text("💬 Открыть заказ", "💬 Open order"),
                url=f"https://funpay.com/orders/{argument}/",
            )
        )
        keyboard.row(
            button(
                token,
                "native_receipt",
                text("📄 Мой резерв товара", "📄 My reserved goods"),
                argument,
            )
        )
        keyboard.row(
            button(
                token,
                "native_resolve",
                text("✓ Отметить проверенным", "✓ Mark reviewed"),
                argument,
            )
        )
        self.menu_render(
            call,
            "<b>#" + escape(argument) + "</b>" + delivery_text(self.cardinal, argument),
            menu_back(keyboard, token, "attention"),
        )

    def menu_native_receipt(self, call, token, argument):
        self.native_row(argument)
        products = receipt_products(self.cardinal, argument)
        if not products:
            return self.menu_render(
                call,
                text(
                    "Резерва товара нет. Проверьте чат заказа и файл товаров.",
                    "No stock reservation. Check the order chat and inventory file.",
                ),
                menu_back(Keyboard(), token, "attention"),
            )
        stream = io.BytesIO("\n".join(products).encode("utf-8"))
        self.bot.send_document(
            call.from_user.id,
            stream,
            visible_file_name=f"reserved-{argument}.txt",
            caption=text(
                "Только для владельца. Перед ручной выдачей проверьте, не получил ли покупатель товар ранее.",
                "Owner only. Before manual delivery check whether the buyer already received these goods.",
            ),
        )

    def menu_native_resolve(self, call, token, argument):
        self.native_row(argument)
        self.menu_store.update(token, pending_resolution=argument)
        keyboard = Keyboard().row(
            button(
                token,
                "native_confirm",
                text("Да, я проверил заказ", "Yes, I checked the order"),
                argument,
            )
        )
        self.menu_render(
            call,
            text(
                "Убрать заказ из списка проверки? Товар повторно не отправляется и в остаток не возвращается.",
                "Remove from review? Goods are neither resent nor returned to stock.",
            ),
            menu_back(keyboard, token, "attention"),
        )

    def menu_native_confirm(self, call, token, argument):
        if not self.menu_store.consume_resolution(token, argument):
            return self.menu_native_resolve(call, token, argument)
        self.native_row(argument)
        journal(self.cardinal).save(argument, "resolved")
        self.menu_native_order(call, token, argument)

    def menu_plugin_health(self, call, token, argument):
        count = len(plugin_rows(self.cardinal))
        page = max(
            0,
            min(
                int(argument) if str(argument).isdecimal() else 0,
                max(0, (count - 1) // 8),
            ),
        )
        keyboard = Keyboard()
        if page:
            keyboard.row(button(token, "plugin_health", "‹", str(page - 1)))
        if count > (page + 1) * 8:
            keyboard.row(button(token, "plugin_health", "›", str(page + 1)))
        self.menu_render(
            call,
            plugin_report(self.cardinal, page),
            menu_back(keyboard, token, "attention"),
        )

    def menu_core_notices(self, call, token, argument):
        path = preference_path(self)
        data = load_state(path)
        if argument == "toggle":
            from cardinal_core.settings_history import change

            data["group_connection"] = not data.get("group_connection", True)
            change(
                self.cardinal,
                call.from_user.id,
                "Core",
                "group_connection",
                "1" if data["group_connection"] else "0",
            )
        enabled = data.get("group_connection", True)
        label = ("🟢 " if enabled else "⚪️ ") + text(
            "Одна карточка сбоя связи", "Single connection incident card"
        )
        keyboard = Keyboard().row(button(token, "core_notices", label, "toggle"))
        self.menu_render(
            call,
            text(
                "🔔 <b>Технические уведомления ядра</b>\n\nСбой и восстановление объединяются в одну карточку. Уведомления о заказах и сообщения плагинов идут по прежним настройкам.",
                "🔔 <b>Core technical notifications</b>\n\nConnection outage and recovery share a card. Order and plugin notifications keep their existing settings.",
            ),
            menu_back(keyboard, token, "settings"),
        )

    def menu_verify_backup(self, call, token, argument):
        if not self.menu_store.begin_read(token, "verify_backup"):
            return
        self.menu_render(
            call,
            text(
                "⏳ Проверяю копию и пробную распаковку…",
                "⏳ Checking backup and trial extraction…",
            ),
            menu_back(Keyboard(), token, "service"),
        )
        Thread(
            target=self.verify_backup_worker, args=(call, token), daemon=True
        ).start()

    def verify_backup_worker(self, call, token):
        from pathlib import Path
        from Utils.backups.service import BackupService

        try:
            result = BackupService(Path.cwd()).verify_restore()
            content = text(
                f"✅ Копия проверена: {result['files']} файлов. Пробная распаковка успешна. Рабочие данные не заменялись.",
                f"✅ Backup verified: {result['files']} files. Trial extraction succeeded. Live data was not replaced.",
            )
        except Exception:
            logging.getLogger("TGBot").exception("Backup trial extraction failed")
            content = text(
                "❌ Копия отсутствует или не прошла проверку. Создайте новую копию; детали в журнале.",
                "❌ Backup missing or verification failed. Create a new backup; see the log for details.",
            )
        finally:
            self.menu_store.finish_read(token)
        self.menu_render(call, content, menu_back(Keyboard(), token, "service"))

    def withdraw_screen(self, quote):
        alerts = alerts_enabled(self.cardinal)
        trend = vars(self).get("withdraw_trend")
        return withdraw_text(quote, trend, alerts), alerts

    def menu_withdraw(self, call, token, argument):
        cached = vars(self).get("withdraw_quote")
        age = time.time() - cached.created_at if cached else None
        limit = (
            WITHDRAW_REFRESH_SECONDS
            if argument == "refresh"
            else WITHDRAW_CACHE_SECONDS
        )
        if cached and age < limit:
            content, alerts = self.withdraw_screen(cached)
            return self.menu_render(call, content, withdraw_keyboard(token, alerts))
        alerts = alerts_enabled(self.cardinal)
        if not getattr(self.cardinal.account, "is_initiated", False):
            return self.menu_render(
                call,
                text(
                    "🔴 Аккаунт FunPay ещё не подключён — расчёт вывода недоступен.",
                    "🔴 The FunPay account is not connected yet; payout estimate unavailable.",
                ),
                withdraw_keyboard(token, alerts),
            )
        if not self.menu_store.begin_read(token, "withdraw"):
            return
        self.menu_render(
            call,
            text(
                "⏳ Проверяю баланс и комиссии вывода на FunPay…",
                "⏳ Checking balance and payout fees on FunPay…",
            ),
            withdraw_keyboard(token, alerts),
        )
        Thread(target=self.withdraw_worker, args=(call, token), daemon=True).start()

    def withdraw_options_for(self, amount):
        cached = vars(self).get("withdraw_options")
        if (
            amount is not None
            and cached
            and time.time() - cached[0] < WITHDRAW_CACHE_SECONDS
        ):
            return cached[1]
        options = self.cardinal.account.get_withdraw_options()
        self.withdraw_options = (time.time(), options)
        return options

    def menu_withdraw_amount(self, call, token, argument):
        self.menu_render(
            call,
            text(
                "✍️ <b>Своя сумма вывода</b>\nНапишите сумму в рублях, например 5000 или 12 500,50 — посчитаю, сколько придёт на карту, по СБП и в USDT. Бот ничего не выводит.",
                "✍️ <b>Custom payout amount</b>\nSend an amount in rubles, such as 5000 or 12500.50, and I will show what arrives on a card, via СБП and in USDT. The bot never withdraws.",
            ),
            menu_back(Keyboard(), token, "withdraw"),
        )
        self.set_state(
            call.message.chat.id,
            call.message.id,
            call.from_user.id,
            MENU_INPUT_STATE,
            {"token": token, "action": "withdraw_amount", "lot_id": None},
        )

    def withdraw_custom(self, call, token, amount):
        if not getattr(self.cardinal.account, "is_initiated", False):
            raise ValueError("FunPay account is not connected")
        if not self.menu_store.begin_read(token, "withdraw_amount"):
            return False
        self.menu_render(
            call,
            text("⏳ Считаю вывод для ", "⏳ Estimating payout for ")
            + money(amount)
            + "…",
            withdraw_keyboard(token, alerts_enabled(self.cardinal), True),
        )
        Thread(
            target=self.withdraw_worker, args=(call, token, amount), daemon=True
        ).start()
        return True

    def withdraw_worker(self, call, token, amount=None):
        account = self.cardinal.account
        alerts = alerts_enabled(self.cardinal)
        try:
            quote = build_quote(
                self.withdraw_options_for(amount), account.calc_withdraw, amount=amount
            )
            if amount is None:
                self.withdraw_quote = quote
            rate = next(
                (item.fee.rate for item in quote.channels if item.channel == CRYPTO),
                None,
            )
            if rate:
                self.withdraw_trend = remember_rate(
                    self.cardinal, rate, evaluate=False
                )[0]
            content, alerts = self.withdraw_screen(quote)
        except Exception:
            logging.getLogger("TGBot").exception("Payout estimate failed")
            content = text(
                "❌ Не удалось получить данные вывода с FunPay. Попробуйте ещё раз через минуту.",
                "❌ Could not load payout data from FunPay. Try again in a minute.",
            )
        finally:
            self.menu_store.finish_read(token)
        self.menu_render(
            call, content, withdraw_keyboard(token, alerts, amount is not None)
        )

    def menu_rate_alerts(self, call, token, argument):
        enabled = argument == "on"
        set_alerts(self.cardinal, enabled)
        logging.getLogger("TGBot").info(
            "Rate drop alerts %s by %s",
            "enabled" if enabled else "disabled",
            call.from_user.id,
        )
        cached = vars(self).get("withdraw_quote")
        if cached is not None:
            content, alerts = self.withdraw_screen(cached)
            return self.menu_render(call, content, withdraw_keyboard(token, alerts))
        self.menu_withdraw(call, token, "-")
