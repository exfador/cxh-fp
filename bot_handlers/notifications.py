from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from FunPayAPI import exceptions
from FunPayAPI.updater.events import *
from tg_bot import utils, keyboards
from Utils import cardinal_tools
from threading import Thread
import time
import handlers as _module_state


def send_new_order_notification_handler(c: Cardinal, e: NewOrderEvent, *args):
    if not c.telegram:
        return
    if e.order.buyer_username in c.blacklist and c.MAIN_CFG["BlockList"].getboolean(
        "blockNewOrderNotification"
    ):
        return
    config_obj = getattr(e, "config_section_obj")
    if e.order.status is not OrderStatuses.PAID:
        delivery_info = _module_state._("ntfc_new_order_not_paid")
    elif not config_obj:
        delivery_info = _module_state._("ntfc_new_order_not_in_cfg")
    elif not c.autodelivery_enabled:
        delivery_info = _module_state._("ntfc_new_order_ad_disabled")
    elif config_obj.getboolean("disable"):
        delivery_info = _module_state._("ntfc_new_order_ad_disabled_for_lot")
    elif c.bl_delivery_enabled and e.order.buyer_username in c.blacklist:
        delivery_info = _module_state._("ntfc_new_order_user_blocked")
    else:
        delivery_info = _module_state._("ntfc_new_order_will_be_delivered")
    text = _module_state._(
        "ntfc_new_order",
        f"{utils.escape(e.order.description)}, {utils.escape(e.order.subcategory_name)}",
        e.order.buyer_username,
        f"{e.order.price} {e.order.currency}",
        e.order.id,
        delivery_info,
    )
    chat = c.account.get_chat_by_name(e.order.buyer_username)
    if chat:
        chat_id = chat.id
    else:
        chat_id = e.order.chat_id
    keyboard = keyboards.new_order(e.order.id, e.order.buyer_username, chat_id)
    Thread(
        target=c.telegram.send_notification,
        args=(text, keyboard, utils.NotificationTypes.new_order),
        daemon=True,
    ).start()


def deliver_goods(c: Cardinal, e: NewOrderEvent, *args):
    chat = c.account.get_chat_by_name(e.order.buyer_username)
    if chat:
        chat_id = chat.id
    else:
        chat_id = e.order.chat_id
    cfg_obj = getattr(e, "config_section_obj")
    delivery_text = cardinal_tools.format_order_text(cfg_obj["response"], e.order)
    amount, goods_left, products = (1, -1, [])
    try:
        if file_name := cfg_obj.get("productsFileName"):
            if c.multidelivery_enabled and (
                not cfg_obj.getboolean("disableMultiDelivery")
            ):
                amount = e.order.amount if e.order.amount else 1
            products, goods_left = cardinal_tools.get_products(
                f"storage/products/{file_name}", amount
            )
            delivery_text = delivery_text.replace(
                "$product", "\n".join(products).replace("\\n", "\n")
            )
    except Exception as exc:
        _module_state.logger.error(
            f"Произошла ошибка при получении товаров для заказа $YELLOW{e.order.id}: {str(exc)}$RESET"
        )
        _module_state.logger.debug("TRACEBACK", exc)
        setattr(e, "error", 1)
        setattr(
            e,
            "error_text",
            f"Произошла ошибка при получении товаров для заказа {e.order.id}: {str(exc)}",
        )
        return
    result = c.send_message(chat_id, delivery_text, e.order.buyer_username)
    if not result:
        _module_state.logger.error(
            f"Не удалось отправить товар для ордера $YELLOW{e.order.id}$RESET."
        )
        setattr(e, "error", 1)
        setattr(
            e,
            "error_text",
            f"Не удалось отправить сообщение с товаром для заказа {e.order.id}.",
        )
        if getattr(result, "sent_messages", ()):
            setattr(e, "delivery_partial", True)
            setattr(e, "delivery_text", delivery_text)
            setattr(e, "goods_left", goods_left)
            setattr(
                e,
                "error_text",
                f"Сообщение для заказа {e.order.id} отправлено частично. "
                "Товары не возвращены в остаток. Проверьте переписку с покупателем.",
            )
            _module_state.logger.error(e.error_text)
        elif file_name and products:
            cardinal_tools.add_products(
                f"storage/products/{file_name}", products, at_zero_position=True
            )
    else:
        _module_state.logger.info(f"Товар для заказа {e.order.id} выдан.")
        setattr(e, "delivered", True)
        setattr(e, "delivery_text", delivery_text)
        setattr(e, "goods_delivered", amount)
        setattr(e, "goods_left", goods_left)


def deliver_product_handler(c: Cardinal, e: NewOrderEvent, *args) -> None:
    if e.order.status is not OrderStatuses.PAID:
        return
    if not c.MAIN_CFG["FunPay"].getboolean("autoDelivery"):
        return
    if e.order.buyer_username in c.blacklist and c.bl_delivery_enabled:
        _module_state.logger.info(
            f"Пользователь {e.order.buyer_username} находится в ЧС и включена блокировка автовыдачи. $YELLOW(ID: {e.order.id})$RESET"
        )
        return
    if (config_section_obj := getattr(e, "config_section_obj")) is None:
        return
    if config_section_obj.getboolean("disable"):
        _module_state.logger.info(
            f'Для лота "{e.order.description}" отключена автовыдача.'
        )
        return
    c.run_handlers(c.pre_delivery_handlers, (c, e))
    _module_state.deliver_goods(c, e, *args)
    c.run_handlers(c.post_delivery_handlers, (c, e))


def send_delivery_notification_handler(c: Cardinal, e: NewOrderEvent):
    if c.telegram is None:
        return
    if getattr(e, "error"):
        text = f"❌ <code>{getattr(e, 'error_text')}</code>"
    else:
        amount = (
            "<b>∞</b>"
            if getattr(e, "goods_left") == -1
            else f"<code>{getattr(e, 'goods_left')}</code>"
        )
        text = f"✅ Успешно выдал товар для ордера <code>{e.order.id}</code>.\n\n🛒 <b><i>Товар:</i></b>\n<code>{utils.escape(getattr(e, 'delivery_text'))}</code>\n\n📋 <b><i>Осталось товаров: </i></b>{amount}"
    Thread(
        target=c.telegram.send_notification,
        args=(text,),
        kwargs={"notification_type": utils.NotificationTypes.delivery},
        daemon=True,
    ).start()


def update_current_lots(c: Cardinal, e: NewOrderEvent):
    _module_state.logger.info("Получаю информацию о лотах...")
    attempts = 3
    while attempts:
        try:
            c.curr_profile = c.account.get_user(c.account.id)
            c.curr_profile_last_tag = e.runner_tag
            break
        except:
            _module_state.logger.error(
                "Произошла ошибка при получении информации о лотах."
            )
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            attempts -= 1
            time.sleep(2)
    else:
        _module_state.logger.error(
            "Не удалось получить информацию о лотах: превышено кол-во попыток."
        )
        return


def update_profile_lots(c: Cardinal, e: NewOrderEvent):
    if c.curr_profile_last_tag != e.runner_tag or c.profile_last_tag == e.runner_tag:
        return
    c.profile_last_tag = e.runner_tag
    lots = c.curr_profile.get_sorted_lots(1)
    for lot_id, lot in lots.items():
        c.profile.update_lot(lot)


def update_lot_state(cardinal: Cardinal, lot: types.LotShortcut, task: int) -> bool:
    attempts = 3
    while attempts:
        try:
            lot_fields = cardinal.account.get_lot_fields(lot.id)
            if task == (1 if lot_fields.active else -1):
                return True
            elif task == 1:
                lot_fields.active = True
                cardinal.account.save_lot(lot_fields)
                _module_state.logger.info(
                    f"Восстановил лот $YELLOW{lot.id} - {lot.description}$RESET."
                )
            elif task == -1:
                lot_fields.active = False
                cardinal.account.save_lot(lot_fields)
                _module_state.logger.info(
                    f"Деактивировал лот $YELLOW{lot.id} - {lot.description}$RESET."
                )
            return True
        except Exception as e:
            if isinstance(e, exceptions.LotParsingError):
                _module_state.logger.error(
                    f"Произошла ошибка при изменении состояния лота $YELLOW{lot.description}$RESET:лот не найден."
                )
                return False
            _module_state.logger.error(
                f"Произошла ошибка при изменении состояния лота $YELLOW{lot.description}$RESET."
            )
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            attempts -= 1
            time.sleep(2)
    _module_state.logger.error(
        f"Не удалось изменить состояние лота $YELLOW{lot.description}$RESET: превышено кол-во попыток."
    )
    return False
