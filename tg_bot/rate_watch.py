import logging
import time
from pathlib import Path
from threading import Thread

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.updates.store import load_state, write_state
from cardinal_core.withdraw_quote import CARD, CRYPTO, CURRENCY, SBP, parse_fee
from tg_bot.core_operations import text

logger = logging.getLogger("CoxerHubBot.rate_watch")
RATE_CHECK_SECONDS = 600
RATE_WINDOW_SECONDS = 86400
RATE_DROP_PERCENT = 1.0
RATE_RESET_PERCENT = 0.3
RATE_POINTS_LIMIT = 500
PREFERENCE = "rate_alerts"


def seller_of(cardinal):
    return str(getattr(cardinal.account, "id", 0) or 0)


def preference_file(cardinal):
    return Path("storage/core/preferences") / f"{seller_of(cardinal)}.json"


def history_file(cardinal):
    return Path("storage/core/rate_history") / f"{seller_of(cardinal)}.json"


def read_state(path):
    try:
        data = load_state(path)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def alerts_enabled(cardinal):
    return bool(read_state(preference_file(cardinal)).get(PREFERENCE, False))


def set_alerts(cardinal, enabled):
    path = preference_file(cardinal)
    data = read_state(path)
    data[PREFERENCE] = bool(enabled)
    write_state(path, data)


def channel_fees(options):
    channels = (options.currencies.get(CURRENCY) or {}).get("channels") or []
    return {row.get("extCurrency"): parse_fee(row.get("feeInfo")) for row in channels}


def valid_points(data, now):
    points = []
    for item in data.get("points") or []:
        if (
            isinstance(item, list)
            and len(item) == 2
            and all(isinstance(value, (int, float)) for value in item)
            and 0 <= now - item[0] <= RATE_WINDOW_SECONDS
            and item[1] > 0
        ):
            points.append(item)
    return points


def remember_rate(cardinal, rate, now=None, evaluate=True):
    now = time.time() if now is None else now
    path = history_file(cardinal)
    data = read_state(path)
    data["points"] = (valid_points(data, now) + [[now, rate]])[-RATE_POINTS_LIMIT:]
    alert = drop_alert(data, rate) if evaluate else None
    write_state(path, data)
    return trend(data), alert


def trend(data):
    points = data.get("points") or []
    if len(points) < 2:
        return None
    moment, peak = max(points, key=lambda item: item[1])
    rate = points[-1][1]
    return {
        "peak": peak,
        "peak_at": moment,
        "rate": rate,
        "drop": (peak - rate) / peak * 100,
    }


def drop_alert(data, rate):
    current = trend(data)
    if current is None:
        return None
    if current["drop"] < RATE_RESET_PERCENT:
        data["alerted"] = None
        return None
    alerted = data.get("alerted")
    limit = alerted * (1 - RATE_DROP_PERCENT / 100) if alerted else None
    if (alerted is None and current["drop"] >= RATE_DROP_PERCENT) or (
        limit is not None and rate <= limit
    ):
        data["alerted"] = rate
        return current
    return None


def number(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def alert_text(alert, fees):
    card = fees.get(CARD) or fees.get(SBP)
    crypto = fees.get(CRYPTO)
    stamp = time.strftime("%d.%m %H:%M", time.localtime(alert["peak_at"]))
    lines = [
        text(
            "📉 <b>Курс USDT на FunPay снижается</b>",
            "📉 <b>FunPay USDT rate is falling</b>",
        ),
        text("Сейчас: ", "Now: ")
        + f"<b>{number(alert['rate'])} ₽</b>"
        + text(" за 1 USDT", " per 1 USDT"),
        text("Максимум за сутки: ", "24 h high: ")
        + f"{number(alert['peak'])} ₽ ({stamp}) → −{alert['drop']:.2f}%",
    ]
    if card and crypto and card.percent is not None and crypto.percent is not None:
        even = alert["rate"] * (1 - card.percent / 100) / (1 - crypto.percent / 100)
        lines.append(
            text(
                f"Курс равенства с картой теперь {even:.2f} ₽: продаёте USDT на P2P дороже — выгоднее вывод криптой.",
                f"Break-even with the card is now {even:.2f} ₽: if P2P buys USDT above it, withdraw in crypto.",
            )
        )
    lines.append(
        text(
            "Отключить: «💸 Вывод: сколько придёт» → тумблер уведомлений.",
            "Turn off: «💸 Payout estimate» → alerts toggle.",
        )
    )
    return "\n".join(lines)


def alert_keyboard():
    return InlineKeyboardMarkup().row(
        InlineKeyboardButton(
            text("💸 Открыть расчёт вывода", "💸 Open payout estimate"),
            callback_data="hub:rate:withdraw:-",
        )
    )


class RateWatch:
    def __init__(self, cardinal, clock=time.time, sleep=time.sleep):
        self.cardinal = cardinal
        self.clock = clock
        self.sleep = sleep

    def start(self):
        Thread(target=self.loop, name="cxh-rate-watch", daemon=True).start()
        return self

    def loop(self):
        while True:
            self.sleep(RATE_CHECK_SECONDS)
            try:
                self.check()
            except Exception:
                logger.debug("TRACEBACK", exc_info=True)

    def check(self):
        if not alerts_enabled(self.cardinal):
            return None
        account = self.cardinal.account
        if not getattr(account, "is_initiated", False):
            return None
        fees = channel_fees(account.get_withdraw_options())
        crypto = fees.get(CRYPTO)
        if crypto is None or not crypto.rate:
            return None
        _, alert = remember_rate(self.cardinal, crypto.rate, self.clock())
        if alert is not None:
            self.notify(alert_text(alert, fees))
        return alert

    def notify(self, content):
        telegram = getattr(self.cardinal, "telegram", None)
        if telegram is None:
            return 0
        sent = 0
        for chat_id in sorted(getattr(telegram, "authorized_users", ()) or ()):
            if not telegram.notification_recipient_allowed(chat_id):
                continue
            try:
                telegram.bot.send_message(
                    int(chat_id), content, reply_markup=alert_keyboard()
                )
                sent += 1
            except Exception:
                logger.debug("TRACEBACK", exc_info=True)
        return sent
