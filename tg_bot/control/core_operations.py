import io
import logging
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
from tg_bot.keyboard_views.menu import menu_back


def button(token, action, label, argument="-"):
    return Button(label, callback_data=f"hub:{token}:{action}:{argument}")


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
