from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
from FunPayAPI.types import OrderShortcut, Order
from FunPayAPI import exceptions, utils as fp_utils
from FunPayAPI.updater.events import *
from tg_bot import utils, keyboards
from Utils import cardinal_tools
from locales.localizer import Localizer
from threading import Thread
import configparser
from datetime import datetime
import logging
import time
import re

LAST_STACK_ID = ""
MSG_LOG_LAST_STACK_ID = ""
logger = logging.getLogger("FunPay CoxerHub.handlers")
localizer = Localizer()
_ = localizer.translate
ORDER_HTML_TEMPLATE = '<a href="https://funpay.com/orders/DELITEST/" class="tc-item">\n   <div class="tc-date" bis_skin_checked="1">\n      <div class="tc-date-time" bis_skin_checked="1">сегодня, $date</div>\n      <div class="tc-date-left" bis_skin_checked="1">только что</div>\n   </div>\n   <div class="tc-order" bis_skin_checked="1">#DELITEST</div>\n   <div class="order-desc" bis_skin_checked="1">\n      <div bis_skin_checked="1">$lot_name</div>\n      <div class="text-muted" bis_skin_checked="1">Автовыдача, Тест</div>\n   </div>\n   <div class="tc-user" bis_skin_checked="1">\n      <div class="media media-user offline" bis_skin_checked="1">\n         <div class="media-left" bis_skin_checked="1">\n            <div class="avatar-photo pseudo-a" tabindex="0" data-href="https://funpay.com/users/000000/" style="background-image: url(/img/layout/avatar.png);" bis_skin_checked="1"></div>\n         </div>\n         <div class="media-body" bis_skin_checked="1">\n            <div class="media-user-name" bis_skin_checked="1">\n               <span class="pseudo-a" tabindex="0" data-href="https://funpay.com/users/000000/">$username</span>\n            </div>\n            <div class="media-user-status" bis_skin_checked="1">был 1.000.000 лет назад</div>\n         </div>\n      </div>\n   </div>\n   <div class="tc-status text-primary" bis_skin_checked="1">Оплачен</div>\n   <div class="tc-price text-nowrap tc-seller-sum" bis_skin_checked="1">999999.0 <span class="unit">₽</span></div>\n</a>'
from bot_handlers.messages import (
    save_init_chats_handler,
    update_threshold_on_initial_chat,
    old_log_msg_handler,
    log_msg_handler,
    update_threshold_on_last_message_change,
    greetings_handler,
    add_old_user_handler,
    send_response_handler,
    old_send_new_msg_notification_handler,
    send_new_msg_notification_handler,
    send_review_notification,
)
from bot_handlers.replies import (
    process_review_handler,
    send_command_notification_handler,
    test_auto_delivery_handler,
    send_categories_raised_notification_handler,
    get_lot_config_by_name,
    check_products_amount,
    log_new_order_handler,
    setup_event_attributes_handler,
)
from bot_handlers.notifications import (
    send_new_order_notification_handler,
    deliver_goods,
    deliver_product_handler,
    send_delivery_notification_handler,
    update_current_lots,
    update_profile_lots,
    update_lot_state,
)
from bot_handlers.chat_sync import chat_sync_initial_handler, chat_sync_message_handler
from bot_handlers.order_reminder import order_reminder_message_handler
from bot_handlers.delivery import (
    update_lots_states,
    update_profiles_handler,
    send_thank_u_message_handler,
    send_order_confirmed_notification_handler,
    send_bot_started_notification_handler,
)

BIND_TO_INIT_MESSAGE = [
    save_init_chats_handler,
    update_threshold_on_initial_chat,
    chat_sync_initial_handler,
]
BIND_TO_LAST_CHAT_MESSAGE_CHANGED = [
    old_log_msg_handler,
    greetings_handler,
    update_threshold_on_last_message_change,
    add_old_user_handler,
    send_response_handler,
    process_review_handler,
    old_send_new_msg_notification_handler,
    send_command_notification_handler,
    test_auto_delivery_handler,
]
BIND_TO_NEW_MESSAGE = [
    log_msg_handler,
    greetings_handler,
    update_threshold_on_last_message_change,
    add_old_user_handler,
    send_response_handler,
    process_review_handler,
    send_new_msg_notification_handler,
    chat_sync_message_handler,
    order_reminder_message_handler,
    send_command_notification_handler,
    test_auto_delivery_handler,
]
BIND_TO_POST_LOTS_RAISE = [send_categories_raised_notification_handler]
BIND_TO_NEW_ORDER = [
    log_new_order_handler,
    setup_event_attributes_handler,
    send_new_order_notification_handler,
    deliver_product_handler,
    update_profiles_handler,
]
BIND_TO_ORDER_STATUS_CHANGED = [
    send_thank_u_message_handler,
    send_order_confirmed_notification_handler,
]
BIND_TO_POST_DELIVERY = [send_delivery_notification_handler]
BIND_TO_POST_START = [send_bot_started_notification_handler]
