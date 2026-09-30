from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from FunPayAPI.security.constants import (
    API_HOST,
    API_LOCALES,
    API_ORIGIN,
    API_SCHEME,
    API_TLS_PORT,
    MAX_URL_LENGTH,
)


def validate_api_url(value: str, base: str = API_ORIGIN) -> str:
    if not isinstance(value, str) or len(value) > MAX_URL_LENGTH:
        raise ValueError("Invalid FunPay URL")
    if any(ord(character) < 32 for character in value) or "\\" in value:
        raise ValueError("Invalid FunPay URL characters")
    parsed = urlsplit(urljoin(base, value))
    allowed = parsed.scheme == API_SCHEME and parsed.hostname == API_HOST
    allowed = allowed and parsed.port in {None, API_TLS_PORT}
    if not allowed or parsed.username is not None or parsed.password is not None:
        raise ValueError("FunPay request must stay on the trusted origin")
    return urlunsplit((API_SCHEME, API_HOST, parsed.path or "/", parsed.query, ""))


def normalize_api_url(value: str, locale: str | None) -> str:
    parsed = urlsplit(validate_api_url(value))
    if parsed.path.startswith("/api/"):
        return parsed.geturl()
    path = parsed.path
    for language in API_LOCALES:
        if path.startswith(f"/{language}/"):
            path = path[len(language) + 1 :]
            break
    if locale in API_LOCALES:
        path = f"/{locale}{path}"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))


def is_api_method(value: str) -> bool:
    return urlsplit(validate_api_url(value)).path.startswith("/api/")


def build_api_query(value: str, parameters: dict) -> str:
    parsed = urlsplit(validate_api_url(value))
    query = urlencode(parameters, doseq=True)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))
