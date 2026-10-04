from datetime import datetime, timedelta, timezone

FUNPAY_TIMEZONE = timezone(timedelta(hours=3))
FUNPAY_FUTURE_TOLERANCE = timedelta(days=2)


def funpay_now():
    return datetime.now(FUNPAY_TIMEZONE).replace(tzinfo=None)


def order_moment(moment, now):
    if moment <= now + FUNPAY_FUTURE_TOLERANCE:
        return moment
    try:
        return moment.replace(year=moment.year - 1)
    except ValueError:
        return moment - timedelta(days=365)


def funpay_timestamp(moment):
    return moment.replace(tzinfo=FUNPAY_TIMEZONE).timestamp()
