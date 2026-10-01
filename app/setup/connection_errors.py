import requests
from telebot.apihelper import (
    ApiHTTPException,
    ApiInvalidJSONException,
    ApiTelegramException,
)


def report_bot_error(console, error):
    if isinstance(error, requests.exceptions.ProxyError):
        console.say("token_proxy_error")
    elif isinstance(error, requests.exceptions.SSLError):
        console.say("token_tls_error")
    elif isinstance(error, requests.Timeout):
        console.say("token_timeout")
    elif isinstance(error, requests.ConnectionError):
        console.say("token_network_error")
    elif isinstance(error, (ApiTelegramException, ApiHTTPException)):
        status = (
            error.error_code
            if isinstance(error, ApiTelegramException)
            else error.result.status_code
        )
        if type(status) is not int:
            console.say("token_response_error")
        elif status in (401, 404):
            console.say("token_unauthorized")
        elif status == 429:
            console.say("token_rate_limit")
        elif status >= 500:
            console.say("token_service_error", status=status)
        else:
            console.say("token_api_error", status=status)
    elif isinstance(error, ApiInvalidJSONException):
        console.say("token_response_error")
    elif isinstance(error, requests.RequestException):
        console.say("token_network_error")
    else:
        console.say("token_internal_error", error_type=type(error).__name__)
