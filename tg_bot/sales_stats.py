import time
from dataclasses import dataclass
from datetime import timedelta
from html import escape

from FunPayAPI.common.enums import OrderStatuses
from Utils.funpay_time import order_moment
from tg_bot.constants.sales_stats import (
    STATS_DAYS,
    STATS_MAX_PAGES,
    STATS_PAGE_PAUSE,
    STATS_TIME_FORMAT,
    STATS_TITLE_LIMIT,
    STATS_TOP_LIMIT,
    STATS_WEEK_DAYS,
)

BUCKETS = ("today", "week", "month", "closed", "paid", "refunded")


class Bucket:
    def __init__(self):
        self.count = 0
        self.money = {}

    def add(self, order):
        self.count += 1
        count, amount = self.money.get(order.currency, (0, 0.0))
        self.money[order.currency] = (count + 1, amount + float(order.price))

    def ordered(self):
        return sorted(self.money.items(), key=lambda item: -item[1][0])

    def total(self):
        return sum(amount for _, amount in self.money.values())


@dataclass
class SalesSummary:
    today: Bucket
    week: Bucket
    month: Bucket
    closed: Bucket
    paid: Bucket
    refunded: Bucket
    top: list
    counted: int
    complete: bool
    made_at: float


def collect_sales(account, now, sleep=time.sleep):
    cutoff = now - timedelta(days=STATS_DAYS)
    orders, start_from = [], None
    for page_number in range(STATS_MAX_PAGES):
        if page_number:
            sleep(STATS_PAGE_PAUSE)
        start_from, page, _, _ = account.get_sales(start_from)
        orders.extend(page)
        if (
            not page
            or not start_from
            or min(order_moment(order.date, now) for order in page) < cutoff
        ):
            return orders, True
    return orders, False


def summarize(orders, now, complete=True, made_at=None):
    starts = {
        "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "week": now - timedelta(days=STATS_WEEK_DAYS),
        "month": now - timedelta(days=STATS_DAYS),
    }
    buckets = {name: Bucket() for name in BUCKETS}
    categories, seen, counted = {}, set(), 0
    for order in orders:
        if order.id in seen:
            continue
        seen.add(order.id)
        moment = order_moment(order.date, now)
        if moment < starts["month"]:
            continue
        counted += 1
        if order.status is OrderStatuses.REFUNDED:
            buckets["refunded"].add(order)
            continue
        closed = order.status is OrderStatuses.CLOSED
        buckets["closed" if closed else "paid"].add(order)
        for period, start in starts.items():
            if moment >= start:
                buckets[period].add(order)
        name = order.subcategory_name or order.description or "—"
        categories.setdefault(name, Bucket()).add(order)
    top = sorted(
        categories.items(), key=lambda item: (-item[1].count, -item[1].total())
    )[:STATS_TOP_LIMIT]
    return SalesSummary(
        **buckets,
        top=top,
        counted=counted,
        complete=complete,
        made_at=made_at or time.time(),
    )


def amount_text(value, decimal="."):
    rounded = round(value)
    if abs(value - rounded) < 0.005:
        return f"{rounded:,}".replace(",", " ")
    whole, fraction = f"{value:,.2f}".split(".")
    return whole.replace(",", " ") + decimal + fraction


def money_text(bucket, decimal="."):
    if not bucket.money:
        return "—"
    return " + ".join(
        f"{amount_text(amount, decimal)} {currency}"
        for currency, (_, amount) in bucket.ordered()
    )


def average_text(bucket, decimal="."):
    if not bucket.money:
        return "—"
    currency, (count, amount) = bucket.ordered()[0]
    return f"{amount_text(amount / count, decimal)} {currency}"


def short_name(name):
    text = " ".join(str(name).split())
    return text if len(text) <= STATS_TITLE_LIMIT else text[:STATS_TITLE_LIMIT] + "…"


def stats_text(summary, translate):
    decimal = translate("menu_stats_decimal")

    def money(bucket):
        return money_text(bucket, decimal)

    if not summary.counted:
        body = translate("menu_stats_empty")
    else:
        parts = [
            translate(
                "menu_stats_periods",
                summary.today.count,
                money(summary.today),
                summary.week.count,
                money(summary.week),
                summary.month.count,
                money(summary.month),
            ),
            translate(
                "menu_stats_month",
                summary.closed.count,
                money(summary.closed),
                summary.paid.count,
                money(summary.paid),
                summary.refunded.count,
                money(summary.refunded),
                average_text(summary.month, decimal),
            ),
        ]
        if summary.top:
            rows = "\n".join(
                translate(
                    "menu_stats_top_row",
                    index,
                    escape(short_name(name)),
                    bucket.count,
                    money(bucket),
                )
                for index, (name, bucket) in enumerate(summary.top, 1)
            )
            parts.append(translate("menu_stats_top", rows))
        body = "\n\n".join(parts)
    made = time.strftime(STATS_TIME_FORMAT, time.localtime(summary.made_at))
    footer = translate("menu_stats_footer", made)
    if not summary.complete:
        footer += "\n" + translate("menu_stats_partial", summary.counted)
    return f"{translate('menu_stats_title')}\n\n{body}\n\n{footer}"
