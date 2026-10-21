import threading
from html import escape

from telebot.types import InlineKeyboardMarkup as Keyboard
from cardinal_core import bulk_review
from cardinal_core.shop_checks import section_for
from tg_bot.action_plans import plan_store, identity
from tg_bot.control.core_operations import button
from tg_bot.keyboard_views.menu import menu_back
from tg_bot.menu_data import cached_lots

LABELS = {
    "up5": "Цена продавца +5%",
    "up10": "Цена продавца +10%",
    "enable": "Включить",
    "disable": "Выключить",
}
RESULTS = {
    "pending": "не выполнялось",
    "done": "проверено",
    "sending": "результат неизвестен — проверить",
    "changed": "пропущено: данные изменились",
    "review": "проверить вручную",
    "error": "ошибка до сохранения",
    "cancelled": "остановлено",
}


class BulkJob:
    def __init__(self, owner, seller, session):
        self.owner, self.seller, self.session = owner, seller, session
        self.stop_event = threading.Event()
        self.closed_event = threading.Event()

    def close(self):
        self.stop_event.set()


class BulkWorkbench:
    def menu_bulk_start(self, call, token, argument):
        session = self.menu_store.get(
            token, call.from_user.id, call.message.chat.id, call.message.id
        )
        matched = {lot.id for lot in cached_lots(self.cardinal, session.query)}
        rows = []
        if self.cardinal.profile is not None:
            if self.cardinal.profile.id != self.cardinal.account.id:
                raise ValueError("Unexpected profile owner")
            for lot in self.cardinal.profile.get_lots():
                if lot.id in matched and section_for(
                    self.cardinal, str(lot.description or "")
                ):
                    rows.append(
                        {
                            "id": lot.id,
                            "title": str(lot.description or "")[:90],
                            "selected": False,
                        }
                    )
        key = plan_store(self).create(
            *identity(self, call, token),
            "selection",
            {"rows": sorted(rows, key=lambda row: row["id"])},
        )
        self.menu_bulk_select(call, token, key + ".0")

    def menu_bulk_select(self, call, token, argument):
        key, page = argument.split(".")
        data = plan_store(self).read(key, *identity(self, call, token), "selection")
        rows = data["rows"]
        page = max(0, min(int(page), max(0, (len(rows) - 1) // 8)))
        keyboard = Keyboard()
        for index in range(page * 8, min(len(rows), page * 8 + 8)):
            row = rows[index]
            keyboard.row(
                button(
                    token,
                    "bulk_choose",
                    ("☑️ " if row["selected"] else "▫️ ")
                    + f"#{row['id']} {row['title'][:28]}",
                    f"{key}.{index}",
                )
            )
        if page:
            keyboard.row(button(token, "bulk_select", "‹", f"{key}.{page-1}"))
        if len(rows) > (page + 1) * 8:
            keyboard.row(button(token, "bulk_select", "›", f"{key}.{page+1}"))
        selected = sum(row["selected"] for row in rows)
        if selected:
            for mode, label in LABELS.items():
                keyboard.row(button(token, "bulk_prepare", label, f"{key}.{mode}"))
        keyboard.row(button(token, "bulk_report", "📋 Последний результат"))
        content = f"📝 <b>Массовые изменения</b>\n\nВыбрано: {selected}. Найдено: {len(rows)}.\nПоказаны лоты с привязкой штатной выдачи ядра, с учётом поиска в «Лотах».\n\nДо 20 выбранных лотов за операцию — это размер пачки, не лимит раздела FunPay. После выбора действия появится предпросмотр."
        self.menu_render(call, content, menu_back(keyboard, token, "workbench"))

    def menu_bulk_choose(self, call, token, argument):
        key, index = argument.split(".")
        index = int(index)
        if index < 0:
            raise ValueError("Invalid selection")
        store = plan_store(self)
        with store.lock:
            data = store.read(key, *identity(self, call, token), "selection")
            row = data["rows"][index]
            if row["selected"] or sum(item["selected"] for item in data["rows"]) < 20:
                row["selected"] = not row["selected"]
            store.replace(key, *identity(self, call, token), "selection", data)
        self.menu_bulk_select(call, token, f"{key}.{index//8}")

    def menu_bulk_prepare(self, call, token, argument):
        key, mode = argument.split(".")
        data = plan_store(self).read(key, *identity(self, call, token), "selection")
        identifiers = [row["id"] for row in data["rows"] if row["selected"]]
        if not self.menu_store.begin_read(token, "bulk_prepare"):
            return
        self.menu_render(
            call,
            "⏳ Получаю свежие поля лотов для предпросмотра. Изменения ещё не применяются.",
            menu_back(Keyboard(), token, "workbench"),
        )
        threading.Thread(
            target=self.bulk_prepare_worker,
            args=(call, token, identifiers, mode),
            daemon=True,
        ).start()

    def bulk_prepare_worker(self, call, token, identifiers, mode):
        try:
            payload = bulk_review.prepare(self.cardinal, identifiers, mode)
            key = plan_store(self).create(
                *identity(self, call, token), "batch", payload
            )
            self.menu_bulk_preview(call, token, key + ".0")
        except Exception:
            self.menu_render(
                call,
                "Не удалось подготовить изменения. Ничего не сохранено. Обновите список лотов и повторите позже.",
                menu_back(Keyboard(), token, "workbench"),
            )
        finally:
            self.menu_store.finish_read(token)

    def menu_bulk_preview(self, call, token, argument):
        key, page = argument.split(".")
        data = plan_store(self).read(key, *identity(self, call, token), "batch")
        rows = data["rows"]
        page = max(0, min(int(page), max(0, (len(rows) - 1) // 5)))
        keyboard = Keyboard()
        content = "📝 <b>Предпросмотр: " + LABELS[data["mode"]] + "</b>"
        content += f"\nВыбрано: {sum(row['selected'] for row in rows)}. Срок подтверждения — 10 минут.\nЦены продавца, не итог покупателя по СБП. Прибыль и себестоимость здесь не рассчитываются."
        for index in range(page * 5, min(len(rows), page * 5 + 5)):
            row = rows[index]
            currency = row.get("currency", "UNKNOWN")
            currency = "валюта формы" if currency == "UNKNOWN" else currency
            content += f"\n\n#{row['id']} · {escape(row['title'])}\n{row['before']} → {row['after']} {escape(currency)} · {'включён' if row['active_before'] else 'выключен'} → {'включён' if row['active_after'] else 'выключен'}"
            keyboard.row(
                button(
                    token,
                    "bulk_exclude",
                    ("☑️ Включён в план" if row["selected"] else "▫️ Исключён")
                    + f" · {row['id']}",
                    f"{key}.{index}",
                )
            )
        if page:
            keyboard.row(button(token, "bulk_preview", "‹", f"{key}.{page-1}"))
        if len(rows) > (page + 1) * 5:
            keyboard.row(button(token, "bulk_preview", "›", f"{key}.{page+1}"))
        if any(row["selected"] for row in rows):
            keyboard.row(
                button(token, "bulk_apply", "✅ Применить выбранные изменения", key)
            )
        self.menu_render(call, content, menu_back(keyboard, token, "workbench"))

    def menu_bulk_exclude(self, call, token, argument):
        key, index = argument.split(".")
        index = int(index)
        if index < 0:
            raise ValueError("Invalid selection")
        store = plan_store(self)
        with store.lock:
            payload = store.read(key, *identity(self, call, token), "batch")
            payload["rows"][index]["selected"] = not payload["rows"][index]["selected"]
            store.replace(key, *identity(self, call, token), "batch", payload)
        self.menu_bulk_preview(call, token, f"{key}.{index//5}")

    def menu_bulk_apply(self, call, token, argument):
        who = identity(self, call, token)
        if not bulk_review.MUTATION_LOCK.acquire(blocking=False):
            return self.menu_render(
                call,
                "Другая операция ещё выполняется. Посмотрите последний результат.",
                menu_back(Keyboard(), token, "workbench"),
            )
        try:
            payload = plan_store(self).consume(argument, *who, "batch")
            if not any(row["selected"] for row in payload["rows"]):
                raise ValueError("No selected offers")
            job = BulkJob(*who)
            from app.shutdown import coordinator

            self.cardinal._core_bulk_job = job
            coordinator().register(job)
            keyboard = Keyboard().row(
                button(token, "bulk_cancel", "⏸ Остановить после текущего запроса")
            )
            self.menu_render(
                call,
                "⏳ Применяю подтверждённый план. Изменившиеся лоты будут пропущены; при неизвестном результате операция остановится.",
                keyboard,
            )
            threading.Thread(
                target=self.bulk_apply_worker,
                args=(call, token, payload, job),
                daemon=True,
            ).start()
        except BaseException:
            if "job" in locals():
                job.closed_event.set()
            bulk_review.MUTATION_LOCK.release()
            raise

    def bulk_apply_worker(self, call, token, payload, job):
        try:
            bulk_review.execute(
                self.cardinal,
                call.from_user.id,
                payload,
                cancelled=lambda: job.stop_event.is_set()
                or not self.menu_user_allowed(call.from_user, call.message.chat),
            )
        except Exception:
            self.menu_render(
                call,
                "Операция остановлена. Откройте последний результат; неподтверждённые сохранения проверьте вручную.",
                menu_back(
                    Keyboard().row(
                        button(token, "bulk_report", "📋 Последний результат")
                    ),
                    token,
                    "workbench",
                ),
            )
        else:
            self.menu_bulk_report(call, token, "0")
        finally:
            job.closed_event.set()
            bulk_review.MUTATION_LOCK.release()

    def menu_bulk_cancel(self, call, token, argument):
        who = identity(self, call, token)
        job = getattr(self.cardinal, "_core_bulk_job", None)
        if job and (job.owner, job.seller, job.session) == who:
            job.close()
        self.menu_render(
            call,
            "Запрошена остановка. Уже начатый запрос завершается; результат смотрите в отчёте.",
            menu_back(
                Keyboard().row(button(token, "bulk_report", "📋 Обновить результат")),
                token,
                "workbench",
            ),
        )

    def menu_bulk_report(self, call, token, argument):
        data = bulk_review.latest(self.cardinal)
        content = "📋 <b>Последняя массовая операция</b>"
        if not data:
            content += "\nОпераций пока не было."
        else:
            content += f"\nОператор: {data['actor']} · " + (
                "операция завершена"
                if data["finished"]
                else "операция не завершена; отправленные запросы требуют проверки"
            )
            for row in data["rows"]:
                content += f"\n#{row['id']}: {RESULTS[row['result']]}"
        self.menu_render(
            call,
            content,
            menu_back(
                Keyboard().row(button(token, "bulk_report", "↻ Обновить")),
                token,
                "workbench",
            ),
        )
