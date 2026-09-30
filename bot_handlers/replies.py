from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from FunPayAPI.types import OrderShortcut
from FunPayAPI.updater.events import *
from tg_bot import utils, keyboards
from app.constants.branding import BRAND_ICON
from app.brand_policy import rebrand_message_signatures
from Utils import cardinal_tools
from threading import Thread
import configparser
from datetime import datetime
import handlers as _module_state


def process_review_handler(
    c: Cardinal, e: NewMessageEvent | LastChatMessageChangedEvent
):
    if not c.old_mode_enabled:
        if isinstance(e, LastChatMessageChangedEvent):
            return
        obj = e.message
        message_type, its_me = (obj.type, obj.i_am_buyer)
        message_text, chat_id = (str(obj), obj.chat_id)
    else:
        obj = e.chat
        message_type, its_me = (
            obj.last_message_type,
            f" {c.account.username} " in str(obj),
        )
        message_text, chat_id = (str(obj), obj.id)
    if (
        message_type
        not in [types.MessageTypes.NEW_FEEDBACK, types.MessageTypes.FEEDBACK_CHANGED]
        or its_me
    ):
        return

    def send_reply():
        try:
            order = c.get_order_from_object(obj)
            if order is None:
                raise Exception("Не удалось получить объект заказа.")
        except:
            _module_state.logger.error(
                f'Не удалось получить информацию о заказе для сообщения: "{message_text}".'
            )
            _module_state.logger.debug("TRACEBACK", exc_info=True)
            return
        if not order.review or not order.review.stars:
            return
        _module_state.logger.info(f"Изменен отзыв на заказ #{order.id}.")
        toggle = f"star{order.review.stars}Reply"
        text = f"star{order.review.stars}ReplyText"
        reply_text = None
        if c.MAIN_CFG["ReviewReply"].getboolean(toggle) and c.MAIN_CFG[
            "ReviewReply"
        ].get(text):
            try:

                def format_text4review(text_: str):
                    max_l = 999
                    text_ = text_[: max_l + 1]
                    if len(text_) > max_l:
                        ln = len(text_)
                        indexes = []
                        for char in (".", "!", "\n"):
                            index1 = text_.rfind(char)
                            indexes.extend([index1, text_[:index1].rfind(char)])
                        text_ = (
                            text_[: max(indexes, key=lambda x: (x < ln - 1, x))]
                            + BRAND_ICON
                        )
                    text_ = text_.strip()
                    while text_.count("\n") > 9 and text.count("\n\n") > 1:
                        text_ = text_[::-1].replace(
                            "\n\n",
                            "\n",
                            min([text_.count("\n\n") - 1, text_.count("\n") - 9]),
                        )[::-1]
                    if text_.count("\n") > 9:
                        text_ = text_[::-1].replace("\n", " ", text_.count("\n") - 9)[
                            ::-1
                        ]
                    return text_

                reply_text = cardinal_tools.format_order_text(
                    rebrand_message_signatures(c.MAIN_CFG["ReviewReply"].get(text)),
                    order,
                )
                reply_text = format_text4review(reply_text)
                c.account.send_review(order.id, reply_text)
            except:
                _module_state.logger.error(
                    f"Произошла ошибка при ответе на отзыв {order.id}."
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
        _module_state.send_review_notification(c, order, chat_id, reply_text)

    Thread(target=send_reply, daemon=True).start()


def send_command_notification_handler(
    c: Cardinal, e: NewMessageEvent | LastChatMessageChangedEvent
):
    if not c.telegram:
        return
    if not c.old_mode_enabled:
        if isinstance(e, LastChatMessageChangedEvent):
            return
        obj, message_text = (e.message, str(e.message))
        chat_id, chat_name, username = (
            e.message.chat_id,
            e.message.chat_name,
            e.message.author,
        )
    else:
        obj, message_text = (e.chat, str(e.chat))
        chat_id, chat_name, username = (
            obj.id,
            obj.name,
            obj.name if obj.unread else c.account.username,
        )
    if c.bl_cmd_notification_enabled and username in c.blacklist:
        return
    command = message_text.strip().lower()
    if (
        command not in c.AR_CFG
        or not c.AR_CFG[command].getboolean("telegramNotification")
        or (not c.AR_CFG[command].getboolean("enabled"))
    ):
        return
    if not c.AR_CFG[command].get("notificationText"):
        text = f"🧑\u200d💻 Пользователь <b><i>{username}</i></b> ввел команду <code>{utils.escape(command)}</code>."
    else:
        text = cardinal_tools.format_msg_text(
            c.AR_CFG[command]["notificationText"], obj
        )
    Thread(
        target=c.telegram.send_notification,
        args=(
            text,
            keyboards.reply(chat_id, chat_name),
            utils.NotificationTypes.command,
        ),
        daemon=True,
    ).start()


def test_auto_delivery_handler(
    c: Cardinal, e: NewMessageEvent | LastChatMessageChangedEvent
):
    if not c.old_mode_enabled:
        if isinstance(e, LastChatMessageChangedEvent):
            return
        obj, message_text, chat_name, chat_id = (
            e.message,
            str(e.message),
            e.message.chat_name,
            e.message.chat_id,
        )
    else:
        obj, message_text, chat_name, chat_id = (
            e.chat,
            str(e.chat),
            e.chat.name,
            e.chat.id,
        )
    if not message_text.startswith("!автовыдача"):
        return
    split = message_text.split()
    if len(split) < 2:
        _module_state.logger.warning("Одноразовый ключ автовыдачи не обнаружен.")
        return
    key = split[1].strip()
    if key not in c.delivery_tests:
        _module_state.logger.warning("Невалидный одноразовый ключ автовыдачи.")
        return
    lot_name = c.delivery_tests[key]
    del c.delivery_tests[key]
    date = datetime.now()
    date_text = date.strftime("%H:%M")
    html = (
        _module_state.ORDER_HTML_TEMPLATE.replace("$username", chat_name)
        .replace("$lot_name", lot_name)
        .replace("$date", date_text)
    )
    fake_order = OrderShortcut(
        "ADTEST",
        lot_name,
        0.0,
        Currency.UNKNOWN,
        chat_name,
        0,
        chat_id,
        types.OrderStatuses.PAID,
        date,
        "Авто-выдача, Тест",
        None,
        html,
    )
    fake_event = NewOrderEvent(e.runner_tag, fake_order)
    c.run_handlers(c.new_order_handlers, (c, fake_event))


def send_categories_raised_notification_handler(
    c: Cardinal, cat: types.Category, error_text: str = ""
) -> None:
    if not c.telegram:
        return
    text = f"⤴️<b><i>Поднял все лоты категории</i></b> <code>{cat.name}</code>\n<tg-spoiler>{error_text}</tg-spoiler>"
    Thread(
        target=c.telegram.send_notification,
        args=(text,),
        kwargs={"notification_type": utils.NotificationTypes.lots_raise},
        daemon=True,
    ).start()


def get_lot_config_by_name(c: Cardinal, name: str) -> configparser.SectionProxy | None:
    for i in c.AD_CFG.sections():
        if i in name:
            return c.AD_CFG[i]
    return None


def check_products_amount(config_obj: configparser.SectionProxy) -> int:
    file_name = config_obj.get("productsFileName")
    if not file_name:
        return 1
    return cardinal_tools.count_products(f"storage/products/{file_name}")


def log_new_order_handler(c: Cardinal, e: NewOrderEvent, *args):
    _module_state.logger.info(f"Новый заказ! ID: $YELLOW#{e.order.id}$RESET")


def setup_event_attributes_handler(c: Cardinal, e: NewOrderEvent, *args):
    config_section_name = None
    config_section_obj = None
    lot_shortcut = None
    lot_id = None
    lot_description = e.order.description
    for lot in sorted(
        list(c.profile.get_sorted_lots(2).get(e.order.subcategory, {}).values()),
        key=lambda l: len(f"{l.server}, {l.side}, {l.description}"),
        reverse=True,
    ):
        temp_desc = ", ".join([i for i in [lot.server, lot.side, lot.description] if i])
        if temp_desc in e.order.description:
            lot_description = temp_desc
            lot_shortcut = lot
            lot_id = lot.id
            break
    for i in range(3):
        matched_lot_names = []
        for lot_name in c.AD_CFG:
            if i == 0:
                rule = lot_description == lot_name
            elif i == 1:
                rule = lot_description.startswith(lot_name)
            else:
                rule = lot_name in lot_description
            if rule:
                matched_lot_names.append(lot_name)
        if matched_lot_names:
            lot_name = max(matched_lot_names, key=len)
            config_section_obj = c.AD_CFG[lot_name]
            config_section_name = lot_name
            break
    attributes = {
        "config_section_name": config_section_name,
        "config_section_obj": config_section_obj,
        "delivered": False,
        "delivery_text": None,
        "goods_delivered": 0,
        "goods_left": None,
        "error": 0,
        "error_text": None,
        "lot_id": lot_id,
        "lot_shortcut": lot_shortcut,
    }
    for i in attributes:
        setattr(e, i, attributes[i])
    if config_section_obj is None:
        _module_state.logger.info("Лот не найден в конфиге авто-выдачи!")
    else:
        _module_state.logger.info("Лот найден в конфиге авто-выдачи!")
