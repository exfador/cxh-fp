from telebot.types import (
    InlineKeyboardButton as Button,
    InlineKeyboardMarkup as Keyboard,
)

from locales.localizer import Localizer
from app.constants.branding import CHAT_URL
from tg_bot.keyboard_views.styled_button import StyledButton
from tg_bot.constants.button_styles import BUTTON_PRIMARY, BUTTON_SUCCESS
from tg_bot import CBT, static_keyboards
from tg_bot.constants.promotion import SOCIAL_SERVICE_LABEL, SOCIAL_SERVICE_URL
from tg_bot.constants.menu import (
    MENU_PREFIX,
    MENU_UNSET_ARGUMENT,
    MENU_AUTOMATION_ROWS,
    MENU_SETTINGS_ROWS,
    MENU_PAGE_SIZE,
    FUNPAY_LOT_URL,
    FUNPAY_CHAT_URL,
    FUNPAY_SALES_URL,
    FUNPAY_BALANCE_URL,
    FUNPAY_ORDER_URL,
)


def menu_button(label, token, action, argument=MENU_UNSET_ARGUMENT, style=None):
    return StyledButton(
        Localizer().translate(label),
        callback_data=f"{MENU_PREFIX}:{token}:{action}:{argument}",
        style=style,
    )


def menu_back(keyboard, token, section="home"):
    if section == "home":
        return keyboard.row(menu_button("menu_home_button", token, "home"))
    return keyboard.row(
        menu_button("gl_back", token, section),
        menu_button("menu_home_button", token, "home"),
    )


def home_keyboard(token):
    keyboard = Keyboard().row(
        menu_button("menu_lots_button", token, "lots", style=BUTTON_PRIMARY),
        menu_button("menu_orders_button", token, "orders", style=BUTTON_PRIMARY),
    )
    keyboard.row(
        legacy_button("mm_autodelivery", "ad"),
        legacy_button("mm_autoresponse", "ar"),
    )
    keyboard.row(
        Button(
            Localizer().translate("mm_plugins"), callback_data=f"{CBT.PLUGINS_LIST}:0"
        ),
        legacy_button("mm_templates", "templates"),
    )
    keyboard.row(
        menu_button("menu_automation_button", token, "automation"),
        menu_button("menu_settings_button", token, "settings"),
    )
    keyboard.row(
        menu_button("menu_account_button", token, "profile"),
        menu_button("menu_service_button", token, "service"),
    )
    keyboard.row(
        menu_button("menu_stats_button", token, "stats"),
        menu_button("menu_refresh_dashboard", token, "refresh_home"),
    )
    keyboard.row(
        Button(Localizer().translate(SOCIAL_SERVICE_LABEL), url=SOCIAL_SERVICE_URL),
        Button(Localizer().translate("menu_join_chat"), url=CHAT_URL),
    )
    return keyboard


def legacy_button(label, section):
    routes = {
        "templates": f"{CBT.TMPLT_LIST}:0",
        "users": f"{CBT.AUTHORIZED_USERS}:0",
        "proxy": f"{CBT.PROXY}:0",
        "configs": CBT.CONFIG_LOADER,
        "chat_sync": CBT.CHAT_SYNC,
        "confirm_reminder": CBT.CONFIRM_REMINDER,
    }
    return Button(
        Localizer().translate(label),
        callback_data=routes.get(section, f"{CBT.CATEGORY}:{section}"),
    )


def section_keyboard(token, rows):
    keyboard = Keyboard()
    for row in rows:
        keyboard.row(*(legacy_button(label, section) for label, section in row))
    return keyboard.row(menu_button("menu_home_button", token, "home"))


def automation_keyboard(token):
    return section_keyboard(token, MENU_AUTOMATION_ROWS)


def settings_keyboard(token):
    return section_keyboard(token, MENU_SETTINGS_ROWS)


def service_keyboard(token):
    from tg_bot.keyboard_views.operator import operator_button

    keyboard = Keyboard().row(
        menu_button("menu_health_button", token, "health"),
        menu_button("menu_logs_button", token, "logs"),
    )
    keyboard.row(
        menu_button("menu_create_backup_button", token, "create_backup"),
        menu_button("menu_backup_button", token, "backup"),
    )
    keyboard.row(
        menu_button("menu_restart_button", token, "restart"),
        menu_button("menu_shutdown_button", token, "shutdown"),
    )
    keyboard.row(
        operator_button("operator_images", "images"),
        operator_button("operator_delivery_test", "delivery_test"),
    )
    keyboard.row(
        operator_button("operator_restore_backup", "restore_backup"),
        operator_button("operator_logs_clear", "logs_clear"),
    )
    keyboard.row(
        operator_button("operator_system", "system"),
        operator_button("operator_about", "about"),
    )
    keyboard.row(
        menu_button("menu_updates_button", token, "updates"),
        menu_button("menu_help_button", token, "help"),
    )
    return keyboard.row(menu_button("menu_home_button", token, "home"))


def lots_keyboard(token, lots, page, total, searching=False):
    keyboard = Keyboard()
    for lot in lots:
        keyboard.row(
            Button(
                str(lot.id) + " · " + lot.title,
                callback_data=f"{MENU_PREFIX}:{token}:lot:{lot.id}",
            )
        )
    add_menu_pages(keyboard, token, "lots", page, total)
    search = [menu_button("menu_search_button", token, "search")]
    if searching:
        search.append(menu_button("menu_all_lots_button", token, "reset_lots"))
    keyboard.row(*search)
    keyboard.row(menu_button("menu_refresh_lots_button", token, "refresh_lots"))
    return menu_back(keyboard, token)


def add_menu_pages(keyboard, token, action, page, total):
    buttons = []
    if page > 0:
        buttons.append(menu_button("menu_previous_button", token, action, page - 1))
    if (page + 1) * MENU_PAGE_SIZE < total:
        buttons.append(menu_button("menu_next_button", token, action, page + 1))
    if buttons:
        keyboard.row(*buttons)


def lot_keyboard(token, lot_id):
    keyboard = Keyboard().row(
        menu_button(
            "menu_other_price_button", token, "price", lot_id, style=BUTTON_SUCCESS
        )
    )
    keyboard.row(
        Button(
            Localizer().translate("menu_open_lot_button"),
            url=FUNPAY_LOT_URL.format(lot_id),
        ),
        menu_button("gl_refresh", token, "lot", lot_id),
    )
    return menu_back(keyboard, token, "lots")


def orders_keyboard(token, orders, page, total):
    keyboard = Keyboard()
    for order in orders:
        keyboard.row(
            Button(
                order.title,
                callback_data=f"{MENU_PREFIX}:{token}:order:{order.identifier}",
            )
        )
    add_menu_pages(keyboard, token, "orders", page, total)
    keyboard.row(
        menu_button("gl_refresh", token, "refresh_orders"),
        menu_button("menu_stats_button", token, "stats"),
    )
    keyboard.row(
        Button(Localizer().translate("menu_open_sales_button"), url=FUNPAY_SALES_URL),
        menu_button("menu_chats_button", token, "chats"),
    )
    return menu_back(keyboard, token)


def order_keyboard(token, identifier):
    keyboard = Keyboard().row(
        Button(
            Localizer().translate("order_open_button"),
            url=FUNPAY_ORDER_URL.format(identifier),
        )
    )
    return menu_back(keyboard, token, "orders")


def stats_keyboard(token):
    keyboard = Keyboard().row(
        menu_button("gl_refresh", token, "refresh_stats"),
        menu_button("menu_orders_button", token, "orders"),
    )
    keyboard.row(
        Button(Localizer().translate("menu_open_sales_button"), url=FUNPAY_SALES_URL)
    )
    return menu_back(keyboard, token)


def chat_keyboard(token):
    keyboard = Keyboard().row(
        Button(Localizer().translate("menu_open_chats_button"), url=FUNPAY_CHAT_URL)
    )
    return menu_back(keyboard, token, "orders")


def account_keyboard(token, profile_url):
    from tg_bot.keyboard_views.operator import operator_button

    keyboard = Keyboard().row(
        Button(Localizer().translate("menu_open_profile_button"), url=profile_url),
        Button(Localizer().translate("menu_balance_button"), url=FUNPAY_BALANCE_URL),
    )
    keyboard.row(
        operator_button("operator_refresh_profile", "refresh_profile"),
        operator_button("operator_change_key", "change_key"),
    )
    keyboard.row(operator_button("operator_watermark", "watermark"))
    return menu_back(keyboard, token)


def restart_keyboard(token):
    return Keyboard().row(
        menu_button("menu_restart_confirm", token, "confirm_restart"),
        menu_button("gl_cancel", token, "service"),
    )


def unknown_command_keyboard():
    translate = Localizer().translate
    return Keyboard().row(
        Button(translate("mm_plugins"), callback_data=f"{CBT.PLUGINS_LIST}:0"),
        Button(translate("menu_home_button"), callback_data=CBT.MAIN),
    )
