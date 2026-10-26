import re
import time
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

CURRENCY = "rub"
CARD = "card_rub"
SBP = "fps"
CRYPTO = "usdt_trc"
CHANNELS = (CARD, SBP, CRYPTO)
EXAMPLE_AMOUNT = 10000.0
PERCENT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
MINIMUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:₽|руб)", re.I)
RATE_RE = re.compile(r"(?:курс|rate)\D{0,12}?(\d+(?:[.,]\d+)?)", re.I)
HOME_RE = re.compile(r"росси|russia|росі", re.I)
AMOUNT_JUNK_RE = re.compile(r"[\s  ₽]|руб(?:лей|ля|ль)?\.?|р\.?$", re.I)
AMOUNT_RE = re.compile(r"\d{1,8}(?:\.\d{1,2})?")
AMOUNT_MIN = 1.0
AMOUNT_MAX = 10_000_000.0


@dataclass(frozen=True)
class Fee:
    percent: float | None
    minimum: float
    rate: float | None
    info: str


@dataclass(frozen=True)
class ChannelQuote:
    channel: str
    name: str
    unit: str
    wallet: str
    fee: Fee
    commission: float | None
    receive: float | None
    exact: bool


@dataclass(frozen=True)
class WithdrawQuote:
    amount: float
    balance: float
    example: bool
    channels: tuple
    breakeven: float | None
    breakeven_from: float | None
    actual_rate: float | None
    created_at: float
    custom: bool = False


def number(text):
    return float(text.replace(",", "."))


def parse_fee(info):
    lines = [line.strip() for line in str(info or "").splitlines() if line.strip()]
    line = next(
        (item for item in lines if HOME_RE.search(item)), lines[0] if lines else ""
    )
    percent = PERCENT_RE.search(line)
    minimum = MINIMUM_RE.search(line)
    rate = RATE_RE.search(str(info or ""))
    return Fee(
        number(percent.group(1)) if percent else None,
        number(minimum.group(1)) if minimum else 0.0,
        number(rate.group(1)) if rate else None,
        str(info or ""),
    )


def exact(value):
    return Decimal(str(value))


def exact_charge(amount, fee):
    return max(exact(amount) * exact(fee.percent) / 100, exact(fee.minimum))


def commission(amount, fee):
    if fee.percent is None:
        return None
    return round(float(exact_charge(amount, fee)), 2)


def local_receive(amount, fee):
    if fee.percent is None:
        return None
    left = exact(amount) - exact_charge(amount, fee)
    if left <= 0:
        return 0.0
    if fee.rate:
        left /= exact(fee.rate)
    return float(left.quantize(Decimal("0.01"), rounding=ROUND_FLOOR))


def mask_wallet(wallet):
    wallet = str(wallet or "").strip()
    if not wallet or "•" in wallet or "*" in wallet:
        return wallet
    if len(wallet) <= 8:
        return "•••"
    return wallet[:5] + "•••" + wallet[-4:]


def channel_rows(options):
    channels = (options.currencies.get(CURRENCY) or {}).get("channels") or []
    found = {item.get("extCurrency"): item for item in channels}
    return [found[name] for name in CHANNELS if name in found]


def quote_channel(row, amount, options, calc):
    channel = row["extCurrency"]
    fee = parse_fee(row.get("feeInfo"))
    wallets = options.wallets.get(channel) or []
    wallet = wallets[0] if wallets else ""
    expected = local_receive(amount, fee)
    try:
        receive = calc(CURRENCY, channel, amount, wallet if channel == CARD else "")
    except Exception:
        receive = None
    trusted = receive is not None and (receive > 0 or not expected)
    unit = "USDT" if channel == CRYPTO else "₽"
    return ChannelQuote(
        channel,
        str(row.get("name") or channel),
        unit,
        mask_wallet(wallet),
        fee,
        commission(amount, fee),
        receive if trusted else expected,
        trusted,
    )


def breakeven(card, crypto):
    if not card or not crypto or crypto.fee.rate is None:
        return None, None
    if card.fee.percent is None or crypto.fee.percent is None:
        return None, None
    rate = (
        crypto.fee.rate * (1 - card.fee.percent / 100) / (1 - crypto.fee.percent / 100)
    )
    limits = [
        item.fee.minimum / (item.fee.percent / 100)
        for item in (card, crypto)
        if item.fee.percent
    ]
    return round(rate, 4), max(limits) if limits else None


def parse_rub_amount(value):
    raw = AMOUNT_JUNK_RE.sub("", str(value or "")).replace(",", ".")
    if not AMOUNT_RE.fullmatch(raw):
        raise ValueError("Amount must be a number of roubles")
    amount = float(raw)
    if not AMOUNT_MIN <= amount <= AMOUNT_MAX:
        raise ValueError("Amount out of range")
    return amount


def build_quote(options, calc, now=None, amount=None):
    balance = float(options.balances.get(CURRENCY) or 0)
    custom = amount is not None
    example = not custom and balance <= 0
    if not custom:
        amount = EXAMPLE_AMOUNT if example else balance
    channels = tuple(
        quote_channel(row, amount, options, calc) for row in channel_rows(options)
    )
    by_name = {item.channel: item for item in channels}
    card = by_name.get(CARD) or by_name.get(SBP)
    crypto = by_name.get(CRYPTO)
    rate, threshold = breakeven(card, crypto)
    actual = None
    if card and crypto and card.receive and crypto.receive:
        actual = round(card.receive / crypto.receive, 4)
    return WithdrawQuote(
        amount,
        balance,
        example,
        channels,
        rate,
        threshold,
        actual,
        time.time() if now is None else now,
        custom,
    )
