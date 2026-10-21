import copy
import secrets
import threading
import time


class ActionPlans:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.plans = {}

    def create(self, owner, seller, session, kind, payload):
        with self.lock:
            self.plans = {
                key: row
                for key, row in self.plans.items()
                if row["expires"] > self.clock()
            }
            if len(self.plans) >= 64:
                raise ValueError("Too many pending previews")
            identifier = secrets.token_hex(6)
            self.plans[identifier] = {
                "owner": owner,
                "seller": seller,
                "session": session,
                "kind": kind,
                "payload": copy.deepcopy(payload),
                "expires": self.clock() + 600,
                "used": False,
            }
            return identifier

    def read(self, identifier, owner, seller, session, kind):
        with self.lock:
            row = self.plans.get(identifier)
            if row is None or row["expires"] <= self.clock() or row["used"]:
                raise ValueError("Preview expired or already applied")
            if (row["owner"], row["seller"], row["session"], row["kind"]) != (
                owner,
                seller,
                session,
                kind,
            ):
                raise ValueError("Preview does not belong to this session")
            return copy.deepcopy(row["payload"])

    def replace(self, identifier, owner, seller, session, kind, payload):
        with self.lock:
            self.read(identifier, owner, seller, session, kind)
            self.plans[identifier]["payload"] = copy.deepcopy(payload)

    def consume(self, identifier, owner, seller, session, kind):
        with self.lock:
            payload = self.read(identifier, owner, seller, session, kind)
            self.plans[identifier]["used"] = True
            return payload


def plan_store(controller):
    with STORE_LOCK:
        return controller.__dict__.setdefault("core_action_plans", ActionPlans())


STORE_LOCK = threading.Lock()


def identity(controller, call, token):
    if not controller.menu_user_allowed(call.from_user, call.message.chat):
        raise PermissionError("Private authorized operator required")
    if (
        controller.menu_store.get(
            token, call.from_user.id, call.message.chat.id, call.message.id
        )
        is None
    ):
        raise PermissionError("Session expired")
    return call.from_user.id, controller.cardinal.account.id, token
