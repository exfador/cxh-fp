import hashlib
import json
import secrets
import threading
import time
from decimal import Decimal, ROUND_UP
from pathlib import Path

from app.updates.store import load_state, write_state
from cardinal_core.shop_checks import section_for
from tg_bot.menu_data import cached_lots
from FunPayAPI.accounts.price_quotes import validate_price

MUTATION_LOCK = threading.Lock()
MODES = {"up5", "up10", "enable", "disable"}


def fingerprint(fields):
    values = dict(fields.renew_fields().fields)
    values.pop("csrf_token", None)
    values["_currency"] = str(fields.currency)
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, default=str).encode()
    ).hexdigest()


def config_fingerprint(config):
    return hashlib.sha256(json.dumps(dict(config), sort_keys=True).encode()).hexdigest()


def state_path(cardinal):
    seller = cardinal.account.id
    if type(seller) is not int or seller <= 0:
        raise ValueError("Account is not ready")
    return Path(f"storage/core/bulk/{seller}.json")


def prepare(cardinal, identifiers, mode):
    if mode not in MODES or not 1 <= len(identifiers) <= 20:
        raise ValueError("Invalid batch")
    owned = {lot.id for lot in cached_lots(cardinal)}
    if len(set(identifiers)) != len(identifiers) or not set(identifiers) <= owned:
        raise ValueError("Offers are not owned")
    rows = []
    for identifier in identifiers:
        if rows:
            time.sleep(0.3)
        fields = cardinal.account.get_lot_fields(identifier)
        if fields.lot_id != identifier:
            raise ValueError("Offer identity changed")
        section = section_for(cardinal, fields.title_ru)
        if section is None:
            continue
        price = validate_price(str(fields.price))
        new = price
        if mode in {"up5", "up10"}:
            new = (price * Decimal("1.05" if mode == "up5" else "1.10")).quantize(
                Decimal("0.01"), rounding=ROUND_UP
            )
            validate_price(str(new))
        active = mode == "enable" if mode in {"enable", "disable"} else fields.active
        rows.append(
            {
                "id": identifier,
                "title": fields.title_ru[:100],
                "before": str(price),
                "after": str(new),
                "currency": getattr(fields.currency, "name", "UNKNOWN"),
                "active_before": fields.active,
                "active_after": active,
                "fingerprint": fingerprint(fields),
                "section": section,
                "config": config_fingerprint(cardinal.AD_CFG[section]),
                "selected": True,
            }
        )
    return {"mode": mode, "rows": rows}


def latest(cardinal):
    return load_state(state_path(cardinal))


def execute(
    cardinal, actor, payload, progress=lambda row: None, cancelled=lambda: False
):
    rows = [dict(row, result="pending") for row in payload["rows"] if row["selected"]]
    report = {
        "id": secrets.token_hex(6),
        "at": time.time(),
        "actor": actor,
        "mode": payload["mode"],
        "rows": rows,
        "finished": False,
    }
    path = state_path(cardinal)
    write_state(path, report)
    profile = cardinal.account.get_user(cardinal.account.id)
    if profile.id != cardinal.account.id:
        raise ValueError("Profile owner changed")
    owned = {lot.id for lot in profile.get_lots()}
    for row in rows:
        if cancelled() or getattr(cardinal, "_process_stopping", False):
            row["result"] = "cancelled"
            break
        try:
            if row["id"] not in owned:
                raise ValueError("Offer is no longer owned")
            fields = cardinal.account.get_lot_fields(row["id"])
            if fields.lot_id != row["id"] or fingerprint(fields) != row["fingerprint"]:
                row["result"] = "changed"
            elif config_fingerprint(cardinal.AD_CFG[row["section"]]) != row["config"]:
                row["result"] = "changed"
            else:
                if cancelled() or getattr(cardinal, "_process_stopping", False):
                    row["result"] = "cancelled"
                    break
                fields.price = float(Decimal(row["after"]))
                fields.active = row["active_after"]
                row["result"] = "sending"
                write_state(path, report)
                cardinal.account.save_lot(fields)
                result = cardinal.account.get_lot_fields(row["id"])
                expected = fingerprint(fields)
                row["result"] = (
                    "done"
                    if result.lot_id == row["id"] and fingerprint(result) == expected
                    else "review"
                )
        except Exception:
            row["result"] = "review" if row["result"] == "sending" else "error"
        write_state(path, report)
        progress(row)
        if row["result"] in {"review", "error"}:
            break
        time.sleep(0.3)
    report["finished"] = True
    write_state(path, report)
    return report
