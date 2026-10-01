from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from FunPayAPI.updater.events import *
from tg_bot import utils, keyboards
from Utils import cardinal_tools
from threading import Thread
import time
import handlers as _module_state


def update_lots_states(cardinal: Cardinal, event: NewOrderEvent):
    if not any([cardinal.autorestore_enabled, cardinal.autodisable_enabled]):
        return
    curr_profile_tag = cardinal.curr_profile_last_tag
    if cardinal.last_state_change_tag == curr_profile_tag:
        return
    cardinal.last_state_change_tag = curr_profile_tag
    lots = cardinal.curr_profile.get_sorted_lots(1)
    deactivated = []
    restored = []
    for lot in cardinal.profile.get_sorted_lots(3)[SubCategoryTypes.COMMON].values():
        if not lot.description:
            continue
        current_task = 0
        config_obj = _module_state.get_lot_config_by_name(cardinal, lot.description)
        if lot.id not in lots:
            if config_obj is None:
                if cardinal.autorestore_enabled:
                    current_task = 1
            elif cardinal.autorestore_enabled and config_obj.get(
                "disableAutoRestore"
            ) in ["0", None]:
                if not cardinal.autodisable_enabled:
                    current_task = 1
                elif _module_state.check_products_amount(config_obj):
                    current_task = 1
        elif config_obj:
            products_count = _module_state.check_products_amount(config_obj)
            if all(
                (
                    not products_count,
                    cardinal.MAIN_CFG["FunPay"].getboolean("autoDisable"),
                    config_obj.get("disableAutoDisable") in ["0", None],
                )
            ):
                current_task = -1
        if current_task:
            result = _module_state.update_lot_state(cardinal, lot, current_task)
            if result:
                if current_task == -1:
                    deactivated.append(lot.description)
                elif current_task == 1:
                    restored.append(lot.description)
            time.sleep(0.5)
    if deactivated and cardinal.telegram is not None:
        lots = "\n".join(deactivated)
        text = f"🔴 <b>Деактивировал лоты:</b>\n        \n<code>{lots}</code>"
        Thread(
            target=cardinal.telegram.send_notification,
            args=(text,),
            kwargs={"notification_type": utils.NotificationTypes.lots_deactivate},
            daemon=True,
        ).start()
    if restored and cardinal.telegram is not None:
        lots = "\n".join(restored)
        text = f"🟢 <b>Активировал лоты:</b>\n\n<code>{lots}</code>"
        Thread(
            target=cardinal.telegram.send_notification,
            args=(text,),
            kwargs={"notification_type": utils.NotificationTypes.lots_restore},
            daemon=True,
        ).start()


def update_profiles_handler(
    cardinal: Cardinal, event: NewOrderEvent | OrdersListChangedEvent, *args
):

    def f(c: Cardinal, e: NewOrderEvent):
        try:
            _module_state.update_current_lots(c, e)
            _module_state.update_profile_lots(c, e)
            _module_state.update_lots_states(c, e)
        except:
            _module_state.logger.warning(
                "Произошла ошибка при обновлении информации о профилях и состояний лотов."
            )
            _module_state.logger.debug("TRACEBACK", exc_info=True)

    if event.runner_tag != cardinal.last_profile_refresh_event_tag:
        cardinal.last_profile_refresh_event_tag = event.runner_tag
        Thread(target=f, args=(cardinal, event), daemon=True).start()


def send_thank_u_message_handler(cardinal: Cardinal, event: OrderStatusChangedEvent):
    if (
        not cardinal.MAIN_CFG["OrderConfirm"].getboolean("sendReply")
        or event.order.status is not types.OrderStatuses.CLOSED
    ):
        return
    text = cardinal_tools.format_order_text(
        cardinal.MAIN_CFG["OrderConfirm"]["replyText"], event.order
    )
    chat = cardinal.account.get_chat_by_name(event.order.buyer_username)
    if chat:
        chat_id = chat.id
    else:
        chat_id = event.order.chat_id
    _module_state.logger.info(
        f"Пользователь $YELLOW{event.order.buyer_username}$RESET подтвердил выполнение заказа $YELLOW{event.order.id}.$RESET"
    )
    _module_state.logger.info(f"Отправляю ответное сообщение ...")
    Thread(
        target=cardinal.send_message,
        args=(chat_id, text, event.order.buyer_username),
        kwargs={"watermark": cardinal.MAIN_CFG["OrderConfirm"].getboolean("watermark")},
        daemon=True,
    ).start()


def send_order_confirmed_notification_handler(
    cardinal: Cardinal, event: OrderStatusChangedEvent
):
    if cardinal.telegram is None:
        return
    if not event.order.status == types.OrderStatuses.CLOSED:
        return
    chat = cardinal.account.get_chat_by_name(event.order.buyer_username)
    if chat:
        chat_id = chat.id
    else:
        chat_id = event.order.chat_id
    Thread(
        target=cardinal.telegram.send_notification,
        args=(
            f'🪙 Пользователь <a href="https://funpay.com/chat/?node={chat_id}">{event.order.buyer_username}</a> подтвердил выполнение заказа <code>{event.order.id}</code>. (<code>{event.order.price} {event.order.currency}</code>)',
            keyboards.new_order(event.order.id, event.order.buyer_username, chat_id),
            utils.NotificationTypes.order_confirmed,
        ),
        daemon=True,
    ).start()


def send_bot_started_notification_handler(c: Cardinal, *args):
    if c.telegram is None:
        return
    text = _module_state._(
        "fpc_init",
        c.VERSION,
        c.account.username,
        c.account.id,
        c.balance.total_rub,
        c.balance.total_usd,
        c.balance.total_eur,
        c.account.active_sales,
    )
    for i in c.telegram.init_messages:
        try:
            c.telegram.bot.edit_message_text(text, i[0], i[1])
        except:
            continue
