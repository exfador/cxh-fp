import re
import threading
import time
from pathlib import Path

from app.updates.store import load_state, write_state

LOCK = threading.RLock()
STATES = frozenset(
    {"accepted", "reserved", "sending", "sent", "review", "failed", "resolved"}
)


class OrderJournal:
    def __init__(self, root, seller):
        self.root = Path(root).resolve()
        self.seller = str(seller or 0)
        if not self.seller.isascii() or not self.seller.isdecimal():
            raise ValueError("Invalid seller")
        self.directory = self.root / "storage/core/orders" / self.seller

    def path(self, order):
        order = str(order)
        if not re.fullmatch(r"[A-Za-z0-9]{1,20}", order):
            raise ValueError("Invalid order")
        return self.directory / (order + ".json")

    def read(self, order):
        return load_state(self.path(order))

    def save(self, order, state=None, status=None):
        with LOCK:
            row = self.read(order) or {"id": str(order), "history": []}
            if state is not None:
                if state not in STATES:
                    raise ValueError("Invalid native delivery state")
                row["native"] = state
            if status is not None:
                row["status"] = str(status)
            label = state or str(status)
            history = row["history"]
            if not history or history[-1]["state"] != label:
                history.append({"state": label, "at": time.time()})
            row["history"] = history[-20:]
            row["updated"] = time.time()
            write_state(self.path(order), row)
            return row

    def claim(self, order):
        with LOCK:
            if self.read(order).get("native"):
                return False
            self.save(order, "accepted")
            return True

    def recent(self, limit=100):
        if not self.directory.exists():
            return []
        paths = sorted(
            self.directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        return [load_state(path) for path in paths[:limit]]

    def pending(self):
        rows = []
        for path in self.directory.glob("*.json"):
            row = load_state(path)
            if row.get("native") in {
                "accepted",
                "reserved",
                "sending",
                "review",
                "failed",
            } and row.get("status") not in {"CLOSED", "REFUNDED"}:
                rows.append(row)
        return sorted(rows, key=lambda row: row.get("updated", 0), reverse=True)


def journal(cardinal):
    return OrderJournal(Path.cwd(), getattr(cardinal.account, "id", 0))


def observe_order(cardinal, event, *args):
    status = getattr(event.order.status, "name", "UNKNOWN")
    journal(cardinal).save(event.order.id, status=status)


def guarded_delivery(cardinal, event, deliver, args):
    store = journal(cardinal)
    if not store.claim(event.order.id):
        return False
    event._core_delivery_guard = True
    try:
        deliver(cardinal, event, *args)
        state = "sent" if getattr(event, "delivered", False) else "review"
        store.save(event.order.id, state)
    except BaseException:
        store.save(event.order.id, "review")
        raise
    finally:
        event._core_delivery_guard = False
    return True
