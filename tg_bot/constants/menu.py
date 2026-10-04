from types import MappingProxyType

MENU_PREFIX = "hub"
MENU_INPUT_STATE = "hub_input"
MENU_SESSION_SECONDS = 86400
MENU_SESSION_LIMIT = 128
MENU_TOKEN_BYTES = 4
MENU_CALLBACK_PARTS = 4
MENU_PAGE_SIZE = 8
MENU_READ_COOLDOWN = 3
MENU_SEARCH_MAX_LENGTH = 120
MENU_TITLE_MAX_LENGTH = 46
MENU_UNSET_ARGUMENT = "-"
MENU_LOGGER = "CoxerHubBot.telegram"
MENU_FAILURE_LOG = "Menu action failed: action=%s error=%s"
MENU_PRIVATE_CHAT = "private"
MENU_NOT_MODIFIED = "message is not modified"
MENU_ORDER_ID_PATTERN = r"[A-Za-z0-9]{1,20}"
MENU_INPUT_ACTIONS = frozenset({"search", "price"})
MENU_ACTION_HANDLERS = MappingProxyType(
    {
        "home": "menu_home",
        "refresh_home": "menu_refresh_home",
        "automation": "menu_automation",
        "settings": "menu_settings",
        "service": "menu_service",
        "updates": "menu_updates",
        "check_updates": "menu_check_updates",
        "help": "menu_help",
        "health": "menu_health",
        "lots": "menu_lots",
        "lot": "menu_lot",
        "price": "menu_price",
        "search": "menu_search",
        "orders": "menu_orders",
        "chats": "menu_chats",
        "profile": "menu_profile",
        "restart": "menu_restart",
        "confirm_restart": "menu_confirm_restart",
        "reset_lots": "menu_reset_lots",
        "refresh_lots": "menu_refresh_lots",
        "refresh_orders": "menu_refresh_orders",
        "order": "menu_order",
        "stats": "menu_stats",
        "refresh_stats": "menu_refresh_stats",
        "logs": "menu_logs",
        "backup": "menu_backup",
        "create_backup": "menu_create_backup",
        "shutdown": "menu_shutdown",
    }
)
MENU_ORDER_LIMIT = 100
MENU_ORDER_CACHE_SECONDS = 120
MENU_ORDER_TEXT_LIMIT = 300
MENU_ORDER_DATE_FORMAT = "%d.%m.%Y %H:%M"
MENU_UPDATED_FORMAT = "%H:%M:%S"
MENU_HOME_ACTIONS = frozenset({"home", "refresh_home"})
MENU_HOME_ROWS = (
    (("menu_lots_button", "lots"), ("menu_orders_button", "orders")),
    (("menu_automation_button", "automation"), ("mm_plugins", "plugins")),
    (("menu_settings_button", "settings"), ("menu_service_button", "service")),
    (("menu_account_button", "profile"), ("menu_help_button", "help")),
)
MENU_AUTOMATION_FIELDS = (
    ("autoRaise", "menu_auto_raise"),
    ("autoResponse", "menu_auto_response"),
    ("autoDelivery", "menu_auto_delivery"),
)
MENU_AUTOMATION_ROWS = (
    (("mm_global", "main"),),
    (("mm_autoresponse", "ar"), ("mm_autodelivery", "ad")),
    (("mm_greetings", "gr"), ("mm_order_confirm", "oc")),
    (("mm_review_reply", "rr"), ("mm_templates", "templates")),
    (("mm_blacklist", "bl"), ("mm_confirm_reminder", "confirm_reminder")),
)
MENU_SETTINGS_ROWS = (
    (("mm_notifications", "tg"), ("mm_new_msg_view", "mv")),
    (("mm_authorized_users", "users"), ("mm_language", "lang")),
    (("mm_proxy", "proxy"), ("mm_configs", "configs")),
    (("mm_chat_sync", "chat_sync"),),
)
FUNPAY_CHAT_URL = "https://funpay.com/chat/"
FUNPAY_SALES_URL = "https://funpay.com/orders/trade"
FUNPAY_BALANCE_URL = "https://funpay.com/account/balance"
FUNPAY_LOT_URL = "https://funpay.com/lots/offer?id={}"
FUNPAY_ORDER_URL = "https://funpay.com/orders/{}/"
FUNPAY_PROFILE_URL = "https://funpay.com/users/{}/"
