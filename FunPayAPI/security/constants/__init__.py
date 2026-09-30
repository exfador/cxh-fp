API_ORIGIN = "https://funpay.com/"
API_HOST = "funpay.com"
API_SCHEME = "https"
API_TLS_PORT = 443
API_LOCALES = frozenset({"en", "uk"})
MAX_URL_LENGTH = 8192
MAX_REQUEST_ATTEMPTS = 10
MAX_RETRY_DELAY_SECONDS = 30
RATE_LIMIT_STATUS = 429
REDIRECT_STATUS_MIN = 300
REDIRECT_STATUS_MAX = 400

HTTP_RETRY_ATTEMPTS = 3
HTTP_RETRY_BACKOFF = 1
HTTP_RETRY_METHODS = frozenset({"GET"})
HTTP_RETRY_STATUSES = frozenset({500, 502, 503, 504})
RETRY_BACKOFF_BASE = 2
REDIRECT_TO_GET_STATUSES = frozenset({301, 302, 303})
BODY_HEADER_NAMES = frozenset({"content-type", "content-length", "transfer-encoding"})
XHR_FORM_HEADERS = {
    "accept": "*/*",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-requested-with": "XMLHttpRequest",
}
SALES_PATH = "orders/trade"
SALES_PAGE_TITLES = frozenset({"мої продажі", "мои продажи", "my sales"})
