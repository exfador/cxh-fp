PROJECT_NAME = "CXH FP"
BRAND_ICON = "🦊"
BRAND_SIGNATURE = f"{BRAND_ICON} {PROJECT_NAME}"
PREVIOUS_PROJECT_NAME = "CXH FPC"
PREVIOUS_BRAND_SIGNATURE = f"{BRAND_ICON} {PREVIOUS_PROJECT_NAME}"
LEGACY_BRAND_SIGNATURES = frozenset(
    {"🐦", "🦜", "fpc", "cardinal", "funpay coxerhub", PREVIOUS_PROJECT_NAME.casefold()}
)
LEGACY_PROJECT_WORDS = ("funpay", "cardinal")
LEGACY_BRAND_STYLIZATIONS = ("ᴄᴀʀᴅɪɴᴀʟ", "ᑕᗩᖇᗪIᑎᗩᒪ")
LEGACY_WEAK_SIGNATURES = frozenset({"fpc", "cardinal"})
LEGACY_BRAND_ICONS = frozenset({"🐦", "🦜"})
SIGNATURE_SEPARATOR = "\n"
LINE_ENDINGS = "\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029"
SIGNATURE_LINE_SEPARATORS = ("\r\n", *LINE_ENDINGS)
MESSAGE_CONFIG_FIELDS = frozenset(
    {"response", "notificationtext", "greetingstext", "replytext"}
    | {f"star{stars}replytext" for stars in range(1, 6)}
)
DEVELOPER_URL = "https://t.me/coxerhub"
CHANNEL_URL = "https://t.me/funpay_coxerhub"
CHAT_URL = "https://t.me/coxerhub_ch"
DEFAULT_MESSAGE_SIGNATURE = (
    f"{BRAND_SIGNATURE} — магазин FunPay.\n"
    f"Канал: {CHANNEL_URL}\n"
    f"Основной канал : {DEVELOPER_URL}"
)
PREVIOUS_MESSAGE_SIGNATURE = DEFAULT_MESSAGE_SIGNATURE.replace(
    PROJECT_NAME, PREVIOUS_PROJECT_NAME
)
PREVIOUS_MESSAGE_SIGNATURE_LINES = tuple(PREVIOUS_MESSAGE_SIGNATURE.splitlines())
MESSAGE_SIGNATURE_HEADER = DEFAULT_MESSAGE_SIGNATURE.splitlines()[0]
SERVICE_NAME = "coxerhub-bot"
SERVICE_PID_FILENAME = "coxerhub-bot.pid"
