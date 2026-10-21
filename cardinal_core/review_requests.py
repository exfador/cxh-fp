import logging
import re
import time
from pathlib import Path
from threading import RLock

from app.updates.store import load_state, write_state
from cardinal_core.message_results import MessageSendFailure
from FunPayAPI.common.enums import OrderStatuses
from Utils.cardinal_tools import format_order_text

logger = logging.getLogger("CoxerHubBot.review_requests")
LOCK = RLock()


def enabled(cardinal):
    return cardinal.MAIN_CFG["OrderConfirm"].getboolean("requestReview", False)


def record_path(seller, order_id):
    if type(seller) is not int or seller <= 0:
        raise ValueError("Invalid seller")
    if not re.fullmatch(r"[A-Za-z0-9]{1,32}", str(order_id)):
        raise ValueError("Invalid order ID")
    return Path(f"storage/core/review_requests/{seller}/{order_id}.json")


def request_review(cardinal, order_id):
    try:
        with LOCK:
            return send_once(cardinal, order_id)
    except Exception:
        logger.warning("Не удалось проверить или отправить просьбу об отзыве.")
        logger.debug("TRACEBACK", exc_info=True)
        return False


def send_once(cardinal, order_id):
    if not enabled(cardinal) or getattr(cardinal, "_process_stopping", False):
        return False
    account = cardinal.account
    seller = account.id
    path = record_path(seller, order_id)
    if path.exists():
        load_state(path)
        return False
    order = account.get_order(order_id)
    if (
        order.id != order_id
        or order.seller_id != seller
        or order.status != OrderStatuses.CLOSED
        or account is not cardinal.account
        or seller != cardinal.account.id
    ):
        return False
    if order.review is not None:
        write_state(path, {"status": "review_exists", "time": time.time()})
        return False
    blocked = {str(name).casefold() for name in getattr(cardinal, "blacklist", ())}
    if str(order.buyer_username).casefold() in blocked:
        return False
    config = cardinal.MAIN_CFG["OrderConfirm"]
    if not enabled(cardinal) or getattr(cardinal, "_process_stopping", False):
        return False
    text = format_order_text(config["replyText"], order).strip()
    if not text or not order.chat_id or not order.buyer_id:
        return False
    write_state(path, {"status": "sending", "time": time.time()})
    try:
        result = cardinal.send_message(
            order.chat_id,
            text,
            order.buyer_username,
            order.buyer_id,
            attempts=1,
            watermark=config.getboolean("watermark"),
        )
        sent = bool(result) and not isinstance(result, MessageSendFailure)
    except Exception:
        write_state(path, {"status": "uncertain", "time": time.time()})
        raise
    write_state(path, {"status": "sent" if sent else "uncertain", "time": time.time()})
    if sent:
        logger.info("Заказ #%s: отправлена просьба оставить отзыв.", order_id)
    else:
        logger.warning(
            "Заказ #%s: результат просьбы об отзыве неизвестен; повтор отключён.",
            order_id,
        )
    return sent
