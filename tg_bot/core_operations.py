import time
from html import escape
from pathlib import Path

from locales.localizer import Localizer
from cardinal_core.order_journal import journal
from tg_bot.connection_monitor import ConnectionMonitor


def text(ru, en):
    return en if Localizer().current_language == "en" else ru


LABELS = {
    "accepted": ("Принят ядром", "Accepted by core"),
    "reserved": ("Товар зарезервирован", "Stock reserved"),
    "sending": (
        "Отправка начата; результат ещё не подтверждён",
        "Sending; result not yet confirmed",
    ),
    "sent": ("Отправка подтверждена FunPay", "Send confirmed by FunPay"),
    "review": ("Нужна проверка переписки", "Check the order chat"),
    "failed": ("Выдача остановлена", "Delivery stopped"),
    "resolved": ("Отмечен оператором как проверенный", "Marked reviewed by operator"),
    "PAID": ("Оплачен", "Paid"),
    "CLOSED": ("Подтверждён покупателем", "Confirmed by buyer"),
    "REFUNDED": ("Возвращён", "Refunded"),
}


def state_label(state):
    return text(*LABELS.get(state, ("Статус неизвестен", "Unknown status")))


def pending_rows(cardinal):
    return journal(cardinal).pending()


def summary(cardinal):
    state, since, kind = ConnectionMonitor(cardinal).evaluate(time.time())
    connected = getattr(cardinal.account, "is_initiated", False) and state == "ok"
    connection = (
        text("🟢 FunPay: связь есть", "🟢 FunPay: connected")
        if connected
        else text("🔴 FunPay: требуется проверка связи", "🔴 FunPay: check connection")
    )
    try:
        count = len(pending_rows(cardinal))
    except (OSError, ValueError, KeyError):
        count = text("ошибка чтения журнала", "journal read error")
    broken = len(vars(cardinal).get("broken_plugins", {}))
    return (
        "\n\n"
        + connection
        + "\n"
        + text(
            f"📦 Незавершённых штатных выдач: {count}",
            f"📦 Unfinished core deliveries: {count}",
        )
        + "\n"
        + text(
            f"🧩 Ошибок загрузки плагинов: {broken}", f"🧩 Plugin load errors: {broken}"
        )
    )


def delivery_text(cardinal, order_id):
    row = journal(cardinal).read(order_id)
    if not row.get("native"):
        return text(
            "\n\n📦 Ядро не зарегистрировало штатную выдачу. Статус стороннего плагина неизвестен — проверьте его панель и чат заказа.",
            "\n\n📦 No core delivery recorded. Third-party delivery status is unknown; check its panel and the order chat.",
        )
    lines = [
        text("\n\n📦 <b>Штатная выдача</b>", "\n\n📦 <b>Core delivery</b>"),
        state_label(row["native"]),
    ]
    for event in row.get("history", [])[-8:]:
        stamp = time.strftime("%d.%m %H:%M:%S", time.localtime(event["at"]))
        lines.append(escape(stamp + " · " + state_label(event["state"])))
    return "\n".join(lines)


def plugin_rows(cardinal):
    rows = []
    for item in getattr(cardinal, "plugins", {}).values():
        mark = "🟢" if item.enabled else "⚪️"
        rows.append(f"{mark} {item.name} · {item.version}"[:180])
    for item in vars(cardinal).get("broken_plugins", {}).values():
        rows.append(f"🔴 {item.name}: {item.error}"[:220])
    return rows


def plugin_report(cardinal, page=0):
    import platform
    import sys

    lines = [
        text("🧩 <b>Диагностика плагинов</b>", "🧩 <b>Plugin diagnostics</b>"),
        escape(
            f"{platform.system()} · Python {sys.version_info.major}.{sys.version_info.minor}"
        ),
        text(
            "Показано состояние загрузки; работоспособность внешних API здесь не проверяется.",
            "Load state only; external APIs are not tested here.",
        ),
    ]
    rows = plugin_rows(cardinal)
    lines.append(
        text(
            f"Всего: {len(rows)} · страница {page+1}",
            f"Total: {len(rows)} · page {page+1}",
        )
    )
    lines.extend(escape(row) for row in rows[page * 8 : page * 8 + 8])
    lines.append(
        text(
            "Замену или откат кода плагина выполняйте его штатным способом. Форматы и обработчики не изменяются.",
            "Use the plugin's own update or rollback procedure. Formats and handlers are unchanged.",
        )
    )
    return "\n".join(lines)


def preference_path(controller):
    return Path("storage/core/preferences") / (
        str(controller.cardinal.account.id or 0) + ".json"
    )
