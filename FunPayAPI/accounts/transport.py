from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Any
from FunPayAPI.common.utils import parse_currency

if TYPE_CHECKING:
    pass
from bs4 import BeautifulSoup
import requests
import json
import time
from FunPayAPI.security.urls import validate_api_url
from urllib.parse import urlsplit
from FunPayAPI.security.request_policy import rate_limit_delay, payload_can_repeat
from FunPayAPI.security.constants import (
    MAX_REQUEST_ATTEMPTS,
    RATE_LIMIT_STATUS,
    REDIRECT_STATUS_MIN,
    REDIRECT_STATUS_MAX,
    REDIRECT_TO_GET_STATUSES,
    BODY_HEADER_NAMES,
    XHR_FORM_HEADERS,
)
from FunPayAPI.common import exceptions
import FunPayAPI.account as _module_state


class RequestTransport:
    def _Account__update_cookies(self, response: requests.Response) -> None:
        cookies = response.cookies.get_dict()
        for k, v in cookies.items():
            if k in ("PHPSESSID", "fav_games"):
                continue
            self.cookies[k] = v

    def method(
        self,
        request_method: Literal["post", "get"],
        api_method: str,
        headers: dict,
        payload: Any,
        exclude_phpsessid: bool = False,
        raise_not_200: bool = False,
        locale: Literal["ru", "en", "uk"] | None = None,
    ) -> requests.Response:
        headers = dict(headers)
        link, cookies = self._prepare_request(
            api_method, request_method, headers, exclude_phpsessid, locale
        )
        kwargs = {
            "method": request_method,
            "headers": headers,
            "timeout": self.requests_timeout,
            "proxies": self.proxy or {},
            "cookies": cookies,
        }
        try:
            response = self._execute_request(link, payload, kwargs)
        except Exception as error:
            self.note_link_failure(error)
            raise
        if response.status_code == 403:
            error = exceptions.UnauthorizedError(response)
            self.note_link_failure(error)
            raise error
        if response.status_code >= 500:
            self.note_link_failure(exceptions.RequestFailedError(response))
        else:
            self.link_ok_time = time.time()
        if response.status_code != 200 and raise_not_200:
            raise exceptions.RequestFailedError(response)
        return response

    def note_link_failure(self, error: Exception) -> None:
        self.link_error = error
        self.link_error_time = time.time()

    def _prepare_request(
        self, api_method, request_method, headers, exclude_phpsessid, locale
    ):
        api_request = self.is_funpay_api_method(api_method)
        cookies = {"golden_key": self.golden_key, **self.cookies}
        if not api_request:
            cookies.setdefault("cookie_prefs", "1")
        if self.phpsessid and (api_request or not exclude_phpsessid):
            cookies["PHPSESSID"] = self.phpsessid
        if not api_request and self.user_agent:
            headers["user-agent"] = self.user_agent
        requested_locale = locale if api_request or request_method == "post" else None
        link = self.normalize_url(api_method, requested_locale)
        locale = locale or self._Account__set_locale
        if (
            not api_request
            and request_method == "get"
            and locale
            and locale != self.locale
        ):
            separator = "&" if "?" in link else "?"
            link += f"{separator}setlocale={locale}"
        return link, cookies

    def _execute_request(self, link, payload, kwargs):
        for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
            response = self.session.request(
                url=link, data=payload, allow_redirects=False, **kwargs
            )
            self._Account__update_cookies(response)
            kwargs["cookies"].update(self.cookies)
            if response.status_code == RATE_LIMIT_STATUS:
                self.last_429_err_time = time.time()
                if attempt == MAX_REQUEST_ATTEMPTS or not payload_can_repeat(payload):
                    break
                self._wait_for_rate_limit(response, link, attempt)
                continue
            redirected = (
                REDIRECT_STATUS_MIN <= response.status_code < REDIRECT_STATUS_MAX
            )
            if not redirected or "Location" not in response.headers:
                return response
            link = validate_api_url(response.headers["Location"], link)
            if urlsplit(link).path.rstrip("/").endswith("/account/login"):
                raise exceptions.UnauthorizedError(response)
            if (
                response.status_code not in REDIRECT_TO_GET_STATUSES
                and not payload_can_repeat(payload)
            ):
                raise exceptions.RequestFailedError(response)
            self._update_redirect_locale(link)
            payload = self._redirect_payload(response.status_code, payload, kwargs)
        raise exceptions.RequestFailedError(response)

    def _wait_for_rate_limit(self, response, link, attempt):
        delay = rate_limit_delay(
            response.headers.get("Retry-After"), attempt, self.last_429_err_time
        )
        _module_state.logger.warning(
            "FunPay rate limit on %s; attempt %s; delay %s seconds",
            urlsplit(link).path,
            attempt,
            delay,
        )
        time.sleep(delay)

    def _update_redirect_locale(self, link):
        for locale in ("en", "uk"):
            if urlsplit(link).path.startswith(f"/{locale}/"):
                self._Account__locale = locale
                return
        self._Account__locale = "ru"

    @staticmethod
    def _redirect_payload(status, payload, kwargs):
        if status not in REDIRECT_TO_GET_STATUSES:
            return payload
        kwargs["method"] = "get"
        kwargs["headers"] = {
            name: value
            for name, value in kwargs["headers"].items()
            if name.lower() not in BODY_HEADER_NAMES
        }
        return None

    def get(self, update_phpsessid: bool = False) -> _module_state.Account:
        if not self.is_initiated:
            self.locale = self._Account__subcategories_parse_locale
        response = self.method(
            "get", "https://funpay.com/", {}, {}, update_phpsessid, raise_not_200=True
        )
        if not self.is_initiated:
            self.locale = self._Account__default_locale
        html_response = response.content.decode()
        parser = BeautifulSoup(html_response, "lxml")
        username = parser.find("div", {"class": "user-link-name"})
        if not username:
            raise exceptions.UnauthorizedError(response)
        self.username = username.text
        self.app_data = json.loads(parser.find("body").get("data-app-data"))
        self._Account__locale = self.app_data.get("locale")
        self.id = self.app_data["userId"]
        self.csrf_token = self.app_data["csrf-token"]
        self._logout_link = parser.find("a", class_="menu-item-logout").get("href")
        active_sales = parser.find("span", {"class": "badge badge-trade"})
        self.active_sales = int(active_sales.text) if active_sales else 0
        balance = parser.find("span", class_="badge badge-balance")
        if balance:
            balance, currency = balance.text.rsplit(" ", maxsplit=1)
            self.total_balance = int(balance.replace(" ", ""))
            self.currency = parse_currency(currency)
        else:
            self.total_balance = 0
        active_purchases = parser.find("span", {"class": "badge badge-orders"})
        self.active_purchases = int(active_purchases.text) if active_purchases else 0
        cookies = response.cookies.get_dict()
        if update_phpsessid or not self.phpsessid:
            self.phpsessid = cookies.get("PHPSESSID", self.phpsessid)
        if not self.is_initiated:
            self._Account__setup_categories(html_response)
        self.last_update = int(time.time())
        self.html = html_response
        self._Account__initiated = True
        return self

    def runner_request(self, payload: dict) -> requests.Response:
        encoded = {
            **payload,
            "csrf_token": self.csrf_token,
            "objects": json.dumps(payload.get("objects", [])),
            "request": json.dumps(payload["request"])
            if payload.get("request")
            else False,
        }
        return self.method(
            "post", "runner/", dict(XHR_FORM_HEADERS), encoded, raise_not_200=True
        )

    def get_payload_data(
        self,
        chats_data: dict[int | str, str | None] | None | list[int | str] = None,
        last_order_event_tag: str | None = None,
        last_msg_event_tag: str | None = None,
        buyer_viewing_ids: list[int | str] | None = None,
        request: None | dict = None,
        include_runner_context: bool = False,
    ) -> dict:
        objects = []
        if chats_data:
            if include_runner_context and self.runner:
                tags = self.runner.chat_node_tags
                msg_ids = self.runner.last_messages_ids
                users_ids = self.runner.users_ids
            else:
                tags, msg_ids, users_ids = ({}, {}, {})
            for chat_id in chats_data:
                literal_chat_id = None
                if chat_id in users_ids:
                    user_id = users_ids[chat_id]
                    id1, id2 = sorted([self.id, user_id])
                    literal_chat_id = f"users-{id1}-{id2}"
                objects.append(
                    {
                        "type": "chat_node",
                        "id": literal_chat_id or chat_id,
                        "tag": tags.get(chat_id) or "00000000",
                        "data": {
                            "node": literal_chat_id or chat_id,
                            "last_message": msg_ids.get(chat_id) or -1,
                            "content": "",
                        },
                    }
                )
        if last_msg_event_tag:
            objects.append(
                {
                    "type": "chat_bookmarks",
                    "id": self.id,
                    "tag": last_msg_event_tag,
                    "data": False,
                }
            )
        if last_order_event_tag:
            objects.append(
                {
                    "type": "orders_counters",
                    "id": self.id,
                    "tag": last_order_event_tag,
                    "data": False,
                }
            )
        if buyer_viewing_ids:
            objects.extend(
                [
                    {"type": "c-p-u", "id": str(i), "tag": "00000000", "data": False}
                    for i in buyer_viewing_ids
                ]
            )
        return {"objects": objects, "request": request}

    def abuse_runner(
        self,
        chats_data: dict[int | str, str | None] | None = None,
        last_order_event_tag: str | None = None,
        last_msg_event_tag: str | None = None,
        buyer_viewing_ids: list[int | str] | None = None,
        request: None | dict = None,
        include_runner_context: bool = False,
    ) -> requests.Response:
        payload_data = self.get_payload_data(
            chats_data,
            last_order_event_tag,
            last_msg_event_tag,
            buyer_viewing_ids,
            request,
            include_runner_context=include_runner_context,
        )
        if self.runner:
            return self.runner.get_result(payload_data)
        else:
            return self.runner_request(payload_data)
