import time
from html import escape

from cardinal_core.withdraw_quote import CARD, CRYPTO, SBP
from tg_bot.core_operations import text
from tg_bot.rate_watch import RATE_CHECK_SECONDS, RATE_DROP_PERCENT

ICONS = {CARD: "💳", SBP: "⚡️", CRYPTO: "🪙"}


def money(value, unit="₽"):
    if value is None:
        return "—"
    formatted = f"{value:,.2f}".replace(",", " ")
    if formatted.endswith(".00"):
        formatted = formatted[:-3]
    return f"{formatted} {unit}"


def rate_text(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def share(percent):
    return rate_text(1 - percent / 100)


def fee_line(item):
    fee = item.fee
    if fee.percent is None:
        return escape(fee.info) or text("Комиссия не указана", "Fee not specified")
    parts = [f"{rate_text(fee.percent)}%"]
    if fee.minimum:
        parts.append(text("мин. ", "min ") + money(fee.minimum))
    return (
        text("Комиссия: ", "Fee: ") + ", ".join(parts) + " → " + money(item.commission)
    )


def channel_block(item):
    title = f"{ICONS.get(item.channel, '•')} <b>{escape(item.name)}</b>"
    if item.wallet:
        title += " · " + escape(item.wallet)
    lines = [title, fee_line(item)]
    if item.fee.rate:
        lines.append(
            text("Курс FunPay: ", "FunPay rate: ")
            + rate_text(item.fee.rate)
            + text(" ₽ за 1 USDT", " ₽ per 1 USDT")
        )
    mark = "" if item.exact else "≈ "
    lines.append(
        text("Придёт: ", "You receive: ")
        + f"<b>{mark}{money(item.receive, item.unit)}</b>"
    )
    return "\n".join(lines)


def formula_block(quote):
    by_name = {item.channel: item for item in quote.channels}
    card = by_name.get(CARD) or by_name.get(SBP)
    crypto = by_name.get(CRYPTO)
    if quote.breakeven is None or not card or not crypto:
        return ""
    value = rate_text(round(quote.breakeven, 2))
    lines = [
        text("📊 <b>Карта или крипта</b>", "📊 <b>Card or crypto</b>"),
        text(
            "Курс = курс FunPay × (1 − комиссия карты) / (1 − комиссия крипты)",
            "Rate = FunPay rate × (1 − card fee) / (1 − crypto fee)",
        ),
        f"{rate_text(crypto.fee.rate)} × {share(card.fee.percent)} / "
        f"{share(crypto.fee.percent)} = <b>{value} ₽</b>",
    ]
    if quote.actual_rate:
        lines.append(
            text("Для этой суммы: ", "For this amount: ")
            + f"{money(card.receive)} / {money(crypto.receive, 'USDT')} = "
            + f"<b>{rate_text(round(quote.actual_rate, 2))} ₽</b>"
            + text(" за 1 USDT", " per 1 USDT")
        )
    return "\n".join(lines)


def watch_block(trend, alerts):
    lines = []
    if trend:
        stamp = time.strftime("%d.%m %H:%M", time.localtime(trend["peak_at"]))
        lines.append(
            text("📉 За сутки: максимум ", "📉 Last 24 h: high ")
            + f"{rate_text(trend['peak'])} ₽ ({stamp}), "
            + text("сейчас ", "now ")
            + f"{rate_text(trend['rate'])} ₽ (−{max(0, trend['drop']):.2f}%)"
        )
    minutes = RATE_CHECK_SECONDS // 60
    drop = rate_text(RATE_DROP_PERCENT)
    lines.append(
        text(
            f"🔔 Уведомления о падении курса включены: напишу, если курс USDT упадёт на {drop}% от максимума за сутки (проверка раз в {minutes} мин).",
            f"🔔 Rate drop alerts are on: I will message you when the USDT rate falls {drop}% below its 24 h high (checked every {minutes} min).",
        )
        if alerts
        else text(
            "🔕 Уведомления о падении курса выключены.",
            "🔕 Rate drop alerts are off.",
        )
    )
    return "\n".join(lines)


def withdraw_text(quote, trend=None, alerts=False):
    head = text(
        "💸 <b>Вывод с FunPay — расчёт</b>", "💸 <b>FunPay payout — estimate</b>"
    )
    if quote.custom:
        head += (
            "\n"
            + text("Ваша сумма: ", "Your amount: ")
            + f"<b>{money(quote.amount)}</b>"
        )
        head += text(" · доступно ", " · available ") + money(quote.balance)
        if quote.amount > quote.balance:
            head += "\n" + text(
                "⚠️ Это больше доступного баланса — столько FunPay сейчас не выведет.",
                "⚠️ More than the available balance; FunPay will not pay out this much now.",
            )
    elif quote.example:
        head += "\n" + text(
            f"Баланс для вывода пуст — пример для {money(quote.amount)}.",
            f"Nothing to withdraw yet — example for {money(quote.amount)}.",
        )
    else:
        head += "\n" + text("Доступно к выводу: ", "Available to withdraw: ")
        head += f"<b>{money(quote.balance)}</b>"
    if not quote.channels:
        return (
            head
            + "\n\n"
            + text(
                "FunPay не показал способы вывода в рублях.",
                "FunPay listed no rouble payout methods.",
            )
        )
    blocks = [head, *(channel_block(item) for item in quote.channels)]
    formula = formula_block(quote)
    if formula:
        blocks.append(formula)
    blocks.append(watch_block(trend, alerts))
    note = text(
        "ℹ️ Суммы посчитал калькулятор FunPay. Бот ничего не выводит — только расчёт.",
        "ℹ️ Amounts come from FunPay's calculator. The bot never withdraws; estimate only.",
    )
    if not all(item.exact for item in quote.channels):
        note += "\n" + text(
            "≈ FunPay не ответил на часть запросов — эти суммы посчитаны по его комиссиям.",
            "≈ FunPay did not answer some requests; those amounts follow its fees.",
        )
    stamp = time.strftime("%H:%M:%S", time.localtime(quote.created_at))
    note += "\n" + text("🕒 Обновлено ", "🕒 Updated ") + stamp
    blocks.append(note)
    return "\n\n".join(blocks)
