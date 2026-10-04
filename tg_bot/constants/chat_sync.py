from types import MappingProxyType

CHAT_SYNC_PATH = "storage/cache/chat_sync.json"
CHAT_SYNC_GROUP_PREFIX = "cxs"
CHAT_SYNC_BIND_COMMAND = "cxh_sync"
CHAT_SYNC_HISTORY_COMMAND = "history"
CHAT_SYNC_SEND_INTERVAL = 3.1
CHAT_SYNC_RETRY_LIMIT = 3
CHAT_SYNC_ECHO_SECONDS = 180
CHAT_SYNC_BATCH_SECONDS = 0.4
CHAT_SYNC_TOPIC_NAME_LIMIT = 128
CHAT_SYNC_TEXT_LIMIT = 4096
CHAT_SYNC_CAPTION_LIMIT = 1024
CHAT_SYNC_HISTORY_LIMIT = 25
CHAT_SYNC_SYNC_LIMIT = 30
CHAT_SYNC_TEMPLATE_LABEL = 48
CHAT_SYNC_MAX_FILE_BYTES = 20 * 1024 * 1024
CHAT_SYNC_ADMIN_STATUSES = frozenset({"administrator", "creator"})
CHAT_SYNC_GONE_STATUSES = frozenset({"left", "kicked"})
CHAT_SYNC_SUPERGROUP = "supergroup"
CHAT_SYNC_TELEBOT_LOGGER = "TeleBot"
CHAT_SYNC_TELEBOT_NOISE = 'parameter "can_send_media_messages" is deprecated'
CHAT_SYNC_OUTGOING_TYPES = ("text", "photo", "document", "sticker")
CHAT_SYNC_THREAD_MISSING = (
    "message thread not found",
    "topic_deleted",
    "thread not found",
)
CHAT_SYNC_THREAD_CLOSED = ("topic_closed",)
CHAT_SYNC_ICONS = MappingProxyType(
    {
        "new": "5417915203100613993",
        "paid": "5431492767249342908",
        "closed": "5350452584119279096",
        "refund": "5312424913615723286",
        "support": "5377438129928020693",
    }
)
CHAT_SYNC_DEFAULT_OPTIONS = MappingProxyType(
    {"own": True, "bot": True, "ads": False, "watermark": True}
)
CHAT_SYNC_OPTIONS = (
    ("own", "cs_opt_own"),
    ("bot", "cs_opt_bot"),
    ("ads", "cs_opt_ads"),
    ("watermark", "cs_opt_watermark"),
)
CHAT_SYNC_HELPER_LIMIT = 9
CHAT_SYNC_HELPER_RETRY_SECONDS = 600
CHAT_SYNC_MESSAGES_PER_BOT = 20
CHAT_SYNC_TOKEN_PATTERN = r"[0-9]{5,16}:[A-Za-z0-9_-]{30,64}"
CHAT_SYNC_HELPER_DOWN = (
    "chat not found",
    "not a member",
    "was kicked",
    "not enough rights to send",
    "have no rights to send",
    "bot was blocked",
)
CHAT_SYNC_HELPER_TOPIC_DENIED = ("not enough rights", "chat_admin_required")
CHAT_SYNC_HELPER_LANGUAGES = ("", "ru", "en")
CHAT_SYNC_HELPER_GROUP_URL = "https://t.me/{}?startgroup=cxh&admin=manage_topics"
CHAT_SYNC_ADD_BOT_URL = (
    "https://t.me/{}?startgroup=cxh&admin=manage_topics+delete_messages+pin_messages"
)
FUNPAY_SALES_BY_BUYER = "https://funpay.com/orders/trade?buyer={}"
FUNPAY_PURCHASES_BY_SELLER = "https://funpay.com/orders/?seller={}"
