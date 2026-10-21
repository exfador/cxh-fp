import time
from html import escape
from threading import Thread

from telebot.types import InlineKeyboardMarkup as Keyboard
from cardinal_core import settings_history
from cardinal_core.shop_checks import inspect_shop
from cardinal_core.training import simulate
from cardinal_core.order_journal import journal
from tg_bot.action_plans import plan_store, identity
from tg_bot.control.core_operations import button
from tg_bot.core_operations import delivery_text, summary, state_label
from tg_bot.keyboard_views.menu import menu_back
from tg_bot.menu_data import cached_orders


class ShopWorkbench:
    def menu_workbench(self, call, token, argument):
        keyboard = Keyboard()
        for action, title in (
            ("shop_check", "🩺 Проверить магазин"),
            ("bulk_start", "📝 Массовые изменения"),
            ("settings_history", "🕘 История настроек"),
            ("training", "🎓 Учебный режим"),
        ):
            keyboard.row(button(token, action, title))
        self.menu_render(
            call,
            "🛠 <b>Управление магазином</b>\n\nПроверки, предпросмотр изменений и обучение. Работа с настройками и выдачей ядра.",
            menu_back(keyboard, token, "service"),
        )

    def menu_shop_check(self, call, token, argument):
        if not self.menu_store.begin_read(token, "shop_check"):
            return
        self.menu_render(
            call,
            "⏳ Проверяю профиль, привязки штатной выдачи, остатки и возраст копии…",
            menu_back(Keyboard(), token, "workbench"),
        )
        Thread(target=self.shop_check_worker, args=(call, token), daemon=True).start()

    def shop_check_worker(self, call, token):
        try:
            rows = inspect_shop(self.cardinal)
            payload = {"rows": rows, "at": time.strftime("%d.%m %H:%M:%S")}
            key = plan_store(self).create(
                *identity(self, call, token), "checks", payload
            )
            self.menu_check_page(call, token, key + ".0")
        except Exception:
            self.menu_render(
                call,
                "Не удалось завершить проверку. Обновите профиль и попробуйте снова.",
                menu_back(Keyboard(), token, "workbench"),
            )
        finally:
            self.menu_store.finish_read(token)

    def menu_check_page(self, call, token, argument):
        key, page = argument.split(".")
        page = int(page)
        data = plan_store(self).read(key, *identity(self, call, token), "checks")
        rows = data["rows"]
        page = max(0, min(page, max(0, (len(rows) - 1) // 6)))
        keyboard = Keyboard()
        content = "🩺 <b>Проверка магазина</b>" + summary(self.cardinal)
        content += "\n\nПрофиль — локальный снимок. Для свежих данных сначала обновите «Лоты». Наличие привязки плагина эта проверка не определяет."
        content += f"\nПроверено: {data['at']} · замечаний: {len(rows)}"
        for row in rows[page * 6 : page * 6 + 6]:
            content += "\n\n• " + escape(row["title"][:180])
            keyboard.row(
                button(token, row["action"], "→ " + row["title"][:45], row["argument"])
            )
        if not rows:
            content += "\n\nПо доступным данным замечаний не найдено. Это не проверка внешних API плагинов."
        if page:
            keyboard.row(button(token, "check_page", "‹", key + f".{page-1}"))
        if len(rows) > (page + 1) * 6:
            keyboard.row(button(token, "check_page", "›", key + f".{page+1}"))
        keyboard.row(
            button(token, "refresh_lots", "↻ Обновить профиль"),
            button(token, "shop_check", "↻ Проверить снова"),
        )
        self.menu_render(call, content, menu_back(keyboard, token, "workbench"))

    def menu_order_explain(self, call, token, argument):
        session = self.menu_store.get(
            token, call.from_user.id, call.message.chat.id, call.message.id
        )
        orders = (
            session.orders
            if session.orders is not None
            else cached_orders(self.cardinal)
        )
        row = journal(self.cardinal).read(argument)
        if not row and not any(item.identifier == argument for item in orders):
            raise ValueError("Unknown order")
        state = row.get("native")
        explanations = {
            "accepted": "Ядро приняло выдачу. Отправка не подтверждена. Проверьте чат и резерв перед ручными действиями.",
            "reserved": "Товар закреплён за заказом. Повторное событие не выдаст второй код.",
            "sending": "Отправка началась, подтверждения результата нет. Проверьте переписку перед повторной выдачей.",
            "sent": "FunPay подтвердил отправку. Это не подтверждение активации товара покупателем.",
            "review": "Автоматическая выдача остановлена для проверки. Посмотрите чат, затем сохранённый резерв.",
            "resolved": "Оператор отметил заказ проверенным. Эта отметка сама по себе ничего не отправляет.",
        }
        content = f"🔎 <b>Разбор заказа #{escape(argument)}</b>" + delivery_text(
            self.cardinal, argument
        )
        if row.get("status"):
            content += "\n\nСтатус по последней записи ядра: " + state_label(
                row["status"]
            )
        content += "\n\n" + explanations.get(
            state,
            "Ядро не располагает подтверждённым результатом выдачи. Проверьте панель плагина и чат заказа; повторную закупку не запускайте без выяснения результата.",
        )
        keyboard = Keyboard()
        from telebot.types import InlineKeyboardButton

        keyboard.row(
            InlineKeyboardButton(
                "💬 Переписка заказа", url=f"https://funpay.com/orders/{argument}/"
            )
        )
        if state:
            keyboard.row(
                button(token, "native_order", "📦 Открыть выдачу и резерв", argument)
            )
        self.menu_render(call, content, menu_back(keyboard, token, "orders"))

    def menu_settings_history(self, call, token, argument):
        rows = list(reversed(settings_history.records(self.cardinal)))
        page = max(
            0,
            min(
                int(argument) if argument.isdecimal() else 0,
                max(0, (len(rows) - 1) // 6),
            ),
        )
        content = "🕘 <b>История настроек ядра</b>\n\nПоследние 200 изменений поддерживаемых переключателей через панель. Секреты и настройки плагинов не записываются. Изменения файлов вручную не отслеживаются."
        keyboard = Keyboard()
        for row in rows[page * 6 : page * 6 + 6]:
            stamp = time.strftime("%d.%m %H:%M", time.localtime(row["at"]))
            name = settings_history.display_name(row["section"], row["option"])
            status = {
                "prepared": "результат записи не подтверждён",
                "applied": "сохранено",
                "failed": "ошибка записи",
            }.get(row["status"], "неизвестно")
            content += f"\n\n{stamp} · оператор {row['actor']}\n{escape(name)}: {'вкл.' if row['before'] == '1' else 'выкл.'} → {'вкл.' if row['after'] == '1' else 'выкл.'} · {status}"
            if row["status"] == "applied":
                keyboard.row(
                    button(token, "settings_undo", "↶ " + name[:42], row["id"])
                )
        if not rows:
            content += "\n\nЗаписей пока нет."
        if page:
            keyboard.row(button(token, "settings_history", "‹", str(page - 1)))
        if len(rows) > (page + 1) * 6:
            keyboard.row(button(token, "settings_history", "›", str(page + 1)))
        self.menu_render(call, content, menu_back(keyboard, token, "workbench"))

    def menu_settings_undo(self, call, token, argument):
        try:
            entry = settings_history.undo_candidate(self.cardinal, argument)
        except ValueError:
            return self.menu_render(
                call,
                "Откат недоступен: настройка уже менялась позже или результат записи не подтверждён.",
                menu_back(Keyboard(), token, "settings_history"),
            )
        key = plan_store(self).create(
            *identity(self, call, token), "undo", {"id": argument}
        )
        name = settings_history.display_name(entry["section"], entry["option"])
        content = f"↶ Вернуть <b>{escape(name)}</b>: {'вкл.' if entry['after'] == '1' else 'выкл.'} → {'вкл.' if entry['before'] == '1' else 'выкл.'}?"
        keyboard = Keyboard().row(
            button(token, "settings_confirm", "Подтвердить откат", key)
        )
        self.menu_render(call, content, menu_back(keyboard, token, "settings_history"))

    def menu_settings_confirm(self, call, token, argument):
        data = plan_store(self).consume(argument, *identity(self, call, token), "undo")
        settings_history.undo(self.cardinal, call.from_user.id, data["id"])
        self.menu_settings_history(call, token, "0")

    def menu_training(self, call, token, argument):
        names = self.cardinal.AD_CFG.sections()
        page = max(
            0,
            min(
                int(argument) if argument.isdecimal() else 0,
                max(0, (len(names) - 1) // 8),
            ),
        )
        key = plan_store(self).create(
            *identity(self, call, token), "training", {"names": names}
        )
        keyboard = Keyboard()
        for index in range(page * 8, min(len(names), page * 8 + 8)):
            keyboard.row(
                button(token, "training_pick", names[index][:45], f"{key}.{index}")
            )
        if page:
            keyboard.row(button(token, "training", "‹", str(page - 1)))
        if len(names) > (page + 1) * 8:
            keyboard.row(button(token, "training", "›", str(page + 1)))
        self.menu_render(
            call,
            "🎓 <b>Учебный режим</b>\n\nВыберите шаблон штатной выдачи. Репетиция использует вымышленный заказ и код; реальные остатки и покупатели не участвуют. Плагины не запускаются."
            + ("\n\nШаблонов пока нет." if not names else ""),
            menu_back(keyboard, token, "workbench"),
        )

    def menu_training_pick(self, call, token, argument):
        key, index = argument.split(".")
        if not index.isascii() or not index.isdecimal():
            raise ValueError("Invalid training template")
        data = plan_store(self).read(key, *identity(self, call, token), "training")
        name = data["names"][int(index)]
        config = dict(self.cardinal.AD_CFG[name])
        case = plan_store(self).create(
            *identity(self, call, token), "simulation", {"name": name, "config": config}
        )
        keyboard = Keyboard()
        for scenario, label in (
            ("success", "✅ Успешная выдача"),
            ("empty", "📭 Нет товара"),
            ("timeout", "⏳ Неизвестный результат отправки"),
        ):
            keyboard.row(button(token, "training_run", label, f"{case}.{scenario}"))
        self.menu_render(
            call,
            "🎓 " + escape(name[:180]) + "\nВыберите учебный сценарий.",
            menu_back(keyboard, token, "training"),
        )

    def menu_training_run(self, call, token, argument):
        from configparser import ConfigParser

        key, scenario = argument.split(".")
        data = plan_store(self).read(key, *identity(self, call, token), "simulation")
        config = ConfigParser(interpolation=None)
        config.optionxform = str
        config.read_dict({"demo": data["config"]})
        stages, parts = simulate(config["demo"], scenario)
        content = "🎓 <b>Учебный результат</b>\n" + "\n".join(
            escape(item) for item in stages
        )
        if parts:
            content += (
                "\n\n<b>Предпросмотр текста, первые 1800 символов</b>\n<pre>"
                + escape("\n\n".join(parts)[:1800])
                + "</pre>"
            )
        content += "\n\nЭто имитация сценария и проверка шаблона, не подтверждение работы FunPay или плагинов."
        self.menu_render(call, content, menu_back(Keyboard(), token, "training"))
