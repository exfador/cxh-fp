from datetime import timezone
from email.utils import parsedate_to_datetime

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from FunPayAPI.security.constants import (
    HTTP_RETRY_ATTEMPTS,
    HTTP_RETRY_BACKOFF,
    HTTP_RETRY_METHODS,
    HTTP_RETRY_STATUSES,
    MAX_RETRY_DELAY_SECONDS,
    RETRY_BACKOFF_BASE,
)


def payload_can_repeat(payload: object) -> bool:
    return payload is None or isinstance(
        payload, (str, bytes, bytearray, dict, list, tuple)
    )


def create_http_adapter() -> HTTPAdapter:
    retries = Retry(
        total=HTTP_RETRY_ATTEMPTS,
        connect=HTTP_RETRY_ATTEMPTS,
        read=HTTP_RETRY_ATTEMPTS,
        status=HTTP_RETRY_ATTEMPTS,
        redirect=0,
        backoff_factor=HTTP_RETRY_BACKOFF,
        status_forcelist=HTTP_RETRY_STATUSES,
        allowed_methods=HTTP_RETRY_METHODS,
        raise_on_status=False,
        respect_retry_after_header=False,
    )
    return HTTPAdapter(max_retries=retries)


def rate_limit_delay(value: str | None, attempt: int, now: float) -> float:
    delay = RETRY_BACKOFF_BASE**attempt
    if value:
        try:
            stripped = value.strip()
            if stripped.isascii() and stripped.isdecimal():
                delay = float(stripped)
            else:
                timestamp = parsedate_to_datetime(stripped)
                timestamp = (
                    timestamp
                    if timestamp.tzinfo
                    else timestamp.replace(tzinfo=timezone.utc)
                )
                delay = timestamp.timestamp() - now
        except (ValueError, TypeError, OverflowError):
            delay = RETRY_BACKOFF_BASE**attempt
    return min(max(delay, 0), MAX_RETRY_DELAY_SECONDS)
