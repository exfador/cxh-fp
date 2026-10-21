import secrets
import threading
import time
from pathlib import Path

from app.updates.store import load_state, write_state

LOCK = threading.RLock()
FIELDS = {
    "FunPay": {
        "autoRaise",
        "autoResponse",
        "autoDelivery",
        "multiDelivery",
        "autoRestore",
        "autoDisable",
        "keepSentMessagesUnread",
    },
    "BlockList": {
        "blockDelivery",
        "blockResponse",
        "blockNewMessageNotification",
        "blockNewOrderNotification",
        "blockCommandNotification",
    },
    "NewMessageView": {
        "includeMyMessages",
        "includeFPMessages",
        "includeBotMessages",
        "notifyOnlyMyMessages",
        "notifyOnlyFPMessages",
        "notifyOnlyBotMessages",
        "showImageName",
    },
    "Greetings": {"sendGreetings", "ignoreSystemMessages", "onlyNewChats"},
    "OrderConfirm": {"sendReply", "watermark", "requestReview"},
    "ReviewReply": {
        "star1Reply",
        "star2Reply",
        "star3Reply",
        "star4Reply",
        "star5Reply",
    },
    "Core": {"group_connection"},
}


def supported(section, option):
    return option in FIELDS.get(section, ())


def display_name(section, option):
    names = {
        "autoRaise": "Автоподнятие лотов",
        "autoResponse": "Автоответы",
        "autoDelivery": "Штатная автовыдача",
        "multiDelivery": "Выдача по количеству",
        "autoRestore": "Автовосстановление лотов",
        "autoDisable": "Автоотключение лотов",
        "keepSentMessagesUnread": "Оставлять отправленные сообщения непрочитанными",
        "blockDelivery": "Запрет выдачи пользователям из ЧС",
        "blockResponse": "Запрет автоответов пользователям из ЧС",
        "blockNewMessageNotification": "ЧС: отключить уведомления о сообщениях",
        "blockNewOrderNotification": "ЧС: отключить уведомления о заказах",
        "blockCommandNotification": "ЧС: отключить уведомления о командах",
        "includeMyMessages": "Показывать мои сообщения",
        "includeFPMessages": "Показывать сообщения FunPay",
        "includeBotMessages": "Показывать сообщения бота",
        "notifyOnlyMyMessages": "Уведомлять только о моих сообщениях",
        "notifyOnlyFPMessages": "Уведомлять только о сообщениях FunPay",
        "notifyOnlyBotMessages": "Уведомлять только о сообщениях бота",
        "showImageName": "Показывать имя изображения",
        "sendGreetings": "Отправлять приветствия",
        "ignoreSystemMessages": "Приветствия: пропускать системные сообщения",
        "onlyNewChats": "Приветствия: только новые чаты",
        "sendReply": "Ответ после подтверждения заказа",
        "requestReview": "Просить отзыв только если его нет",
        "watermark": "Подпись ответа после подтверждения",
        "group_connection": "Одна карточка сбоя связи",
    }
    if section == "ReviewReply" and option.startswith("star"):
        return "Ответ на отзыв: " + option[4] + " звёзд"
    return names.get(option, section + " / " + option)


def history_path(cardinal):
    seller = getattr(cardinal.account, "id", 0) or 0
    if type(seller) is not int or seller < 0:
        raise ValueError("Invalid account")
    return Path(f"storage/core/settings/{seller}.json")


def records(cardinal):
    return load_state(history_path(cardinal)).get("entries", [])


def current(cardinal, section, option):
    if section == "Core":
        path = Path(f"storage/core/preferences/{cardinal.account.id or 0}.json")
        return "1" if load_state(path).get(option, True) else "0"
    return cardinal.MAIN_CFG[section][option]


def persist(cardinal, section, option, value):
    if section == "Core":
        path = Path(f"storage/core/preferences/{cardinal.account.id or 0}.json")
        data = load_state(path)
        data[option] = value == "1"
        write_state(path, data)
        return
    previous = cardinal.MAIN_CFG[section][option]
    cardinal.MAIN_CFG[section][option] = value
    try:
        cardinal.save_config(cardinal.MAIN_CFG, "configs/_main.cfg")
    except Exception:
        cardinal.MAIN_CFG[section][option] = previous
        raise


def change(cardinal, actor, section, option, value, expected=None, undo_of=None):
    if not supported(section, option) or value not in {"0", "1"}:
        raise ValueError("Unsupported setting")
    with LOCK:
        previous = current(cardinal, section, option)
        if previous not in {"0", "1"} or expected is not None and previous != expected:
            raise ValueError("Setting changed since preview")
        rows = records(cardinal)
        entry = {
            "id": secrets.token_hex(6),
            "at": time.time(),
            "actor": int(actor),
            "section": section,
            "option": option,
            "before": previous,
            "after": value,
            "status": "prepared",
            "undo_of": undo_of,
        }
        rows = (rows + [entry])[-200:]
        write_state(history_path(cardinal), {"entries": rows})
        try:
            persist(cardinal, section, option, value)
        except Exception:
            entry["status"] = "failed"
            write_state(history_path(cardinal), {"entries": rows})
            raise
        entry["status"] = "applied"
        write_state(history_path(cardinal), {"entries": rows})
        return entry


def undo_candidate(cardinal, identifier):
    rows = records(cardinal)
    entry = next((row for row in rows if row["id"] == identifier), None)
    if entry is None or entry["status"] != "applied":
        raise ValueError("No confirmed change")
    key = entry["section"], entry["option"]
    latest = next(
        row for row in reversed(rows) if (row["section"], row["option"]) == key
    )
    if (
        latest["id"] != identifier
        or current(cardinal, key[0], key[1]) != entry["after"]
    ):
        raise ValueError("A newer change exists")
    return entry


def undo(cardinal, actor, identifier):
    with LOCK:
        entry = undo_candidate(cardinal, identifier)
        return change(
            cardinal,
            actor,
            entry["section"],
            entry["option"],
            entry["before"],
            expected=entry["after"],
            undo_of=identifier,
        )
