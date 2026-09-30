from app.constants.branding import BRAND_SIGNATURE, DEVELOPER_URL
from app.constants.runtime import VERSION

PROFILE_LANGUAGES = ("", "ru", "en", "uk")
PROFILE_TIMEOUT_SECONDS = 10
PROFILE_CACHE_LIMIT_BYTES = 4096
PROFILE_CACHE_MODE = 0o600
PROFILE_SYNC_THREAD_NAME = "telegram-profile-branding"
PROFILE_DIRECTORY = "bot-profile"
PROFILE_AVATAR_PATH = f"{PROFILE_DIRECTORY}/avatar.jpg"
PROFILE_CACHE_PATH = "storage/cache/bot_profile.json"
PROFILE_PHOTO_METHOD = "setMyProfilePhoto"
PROFILE_PHOTO_ATTACHMENT = "avatar"
PROFILE_PHOTO_TYPE = "static"
PROFILE_PHOTO_MIME = "image/jpeg"
PROFILE_PHOTO_FILENAME = "avatar.jpg"
PROFILE_CHANNEL_URL = "https://t.me/funpay_coxerhub"
PROFILE_DESCRIPTION_RU = f"{BRAND_SIGNATURE} · {VERSION}\n\nВаш магазин FunPay в Telegram.\n\n📦 Лоты, цены и выдача товаров\n🧾 Заказы и сообщения покупателей\n💬 Ответы, отзывы и шаблоны\n🧩 Плагины для магазина\n\nНачать: /start или /menu\n\n📣 Канал: @funpay_coxerhub\n{PROFILE_CHANNEL_URL}\n👤 Разработчик и связь: @coxerhub\n{DEVELOPER_URL}"
PROFILE_DESCRIPTIONS = {
    "": PROFILE_DESCRIPTION_RU,
    "ru": PROFILE_DESCRIPTION_RU,
    "en": f"{BRAND_SIGNATURE} · {VERSION}\n\nYour FunPay store in Telegram.\n\n📦 Offers, prices and delivery\n🧾 Orders and buyer messages\n💬 Replies, reviews and templates\n🧩 Store plugins\n\nStart with /start or /menu\n\n📣 Channel: @funpay_coxerhub\n{PROFILE_CHANNEL_URL}\n👤 Developer and contact: @coxerhub\n{DEVELOPER_URL}",
    "uk": "",
}
PROFILE_SHORT_DESCRIPTION = f"Лоты, заказы и выдача на FunPay.\nКанал: {PROFILE_CHANNEL_URL}\nСвязь: {DEVELOPER_URL}"
PROFILE_SHORT_DESCRIPTION_EN = f"FunPay offers, orders and delivery.\nChannel: {PROFILE_CHANNEL_URL}\nContact: {DEVELOPER_URL}"
PROFILE_TEXT_LIMIT_BYTES = 4096
PROFILE_TEXT_LIMITS = {"description": 512, "short_description": 120}
PROFILE_TEXT_FILES = {
    ("", "description"): "description.txt",
    ("ru", "description"): "description.txt",
    ("en", "description"): "description.en.txt",
    ("", "short_description"): "short-description.txt",
    ("ru", "short_description"): "short-description.txt",
    ("en", "short_description"): "short-description.en.txt",
}
PROFILE_FIELDS = (
    ("Name", "name"),
    ("Description", "description"),
    ("ShortDescription", "short_description"),
)
