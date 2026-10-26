from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from FunPayAPI.common import exceptions
from FunPayAPI.security.constants import XHR_FORM_HEADERS

BALANCE_PAGE = "account/balance"
CALC_PATH = "withdraw/calc"
NUMBER_RE = re.compile(r"\d[\d\s  .,]*")
SPACES_RE = re.compile(r"[\s  ]")


@dataclass(frozen=True)
class WithdrawOptions:
    currencies: dict = field(default_factory=dict)
    wallets: dict = field(default_factory=dict)
    balances: dict = field(default_factory=dict)


def parse_amount(text: str | None) -> float | None:
    match = NUMBER_RE.search(text or "")
    if not match:
        return None
    raw = SPACES_RE.sub("", match.group()).rstrip(".,")
    raw = raw.replace(",", "") if "." in raw else raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_balances(parser: BeautifulSoup) -> dict:
    balances = {}
    select = parser.find("select", {"name": "currency_id"})
    for option in select.find_all("option") if select else []:
        content = BeautifulSoup(option.get("data-content", ""), "lxml")
        value = content.find("span", {"class": "payment-value"})
        amount = parse_amount(value.get_text() if value else "")
        if option.get("value") and amount is not None:
            balances[option["value"]] = amount
    return balances


def parse_withdraw_page(parser: BeautifulSoup) -> WithdrawOptions:
    box = parser.find("div", {"class": "withdraw-box"})
    if box is None or not box.get("data-data"):
        raise ValueError("FunPay withdraw form not found")
    data = json.loads(box["data-data"])
    wallets = {
        name: [str(item) for item in (value or {}).get("wallets") or []]
        for name, value in (data.get("extCurrencies") or {}).items()
    }
    return WithdrawOptions(
        data.get("currencies") or {}, wallets, parse_balances(parser)
    )


class WithdrawQuotes:
    def get_withdraw_options(self) -> WithdrawOptions:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        response = self.method(
            "get", BALANCE_PAGE, {"accept": "*/*"}, {}, raise_not_200=True
        )
        parser = BeautifulSoup(response.content.decode(), "lxml")
        if not parser.find("div", {"class": "user-link-name"}):
            raise exceptions.UnauthorizedError(response)
        self._Account__update_csrf_token(parser)
        token = parser.find("input", {"name": "csrf_token"})
        if token is not None and token.get("value"):
            self.csrf_token = token["value"]
        return parse_withdraw_page(parser)

    def calc_withdraw(
        self, currency: str, channel: str, amount: float, wallet: str = ""
    ) -> float:
        if not self.is_initiated:
            raise exceptions.AccountNotInitiatedError()
        payload = {
            "csrf_token": self.csrf_token,
            "preview": "1",
            "currency_id": currency,
            "ext_currency_id": channel,
            "wallet": wallet,
            "amount_int": f"{amount:.2f}",
        }
        response = self.method(
            "post", CALC_PATH, dict(XHR_FORM_HEADERS), payload, raise_not_200=True
        )
        data = response.json()
        if data.get("error"):
            raise exceptions.RequestFailedError(response)
        return float(data.get("amount_ext") or 0)
