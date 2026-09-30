IGNORED_INPUT_TYPES = frozenset({"button", "submit", "reset", "file", "image"})
CHECKBOX_VALUE = "on"
OFFER_FORM_SELECTOR = "form.form-offer-editor"
OFFER_FORM_MISSING = "Offer editor form is missing"
OFFER_CATEGORY_MISSING = "Offer category is missing"
CURRENCY_FORM_MISSING = "Currency editor form is missing"
OFFER_EMPTY_METADATA = "{}"
OFFER_METADATA_INVALID = "Offer metadata must be an object"
PUBLIC_OFFER_PATHS = frozenset({"/lots/offer", "/chips/offer"})
MAX_OFFER_ID_LENGTH = 128
MAX_QUERY_FIELDS = 32
OFFER_LINK_INVALID = "Invalid public offer link"
LOT_NOT_FOUND_TITLES = frozenset(
    {"Предложение не найдено", "Пропозицію не знайдено", "Offer not found"}
)
LOT_DESCRIPTION_LABELS = {
    "Краткое описание": "short",
    "Короткий опис": "short",
    "Short description": "short",
    "Подробное описание": "full",
    "Докладний опис": "full",
    "Detailed description": "full",
}
LOT_IMAGE_LABELS = frozenset({"Картинки", "Зображення", "Images"})
MESSAGE_PARSE_FAILURE = "Unable to parse the delivered message response"
OFFER_CATEGORY_LINK_MISSING = "Offer category link is missing"
OFFER_PRICE_INVALID = "Offer price must be finite and non-negative"
CHIP_EXCLUDED_FIELDS = frozenset({"query"})
CHAT_NOT_FOUND = "Chat not found"
CHAT_PLACEHOLDER_NAMES = frozenset({"Чат", "Chat"})
CHAT_MEMBER_INVALID = "Private chat membership is invalid"
CHAT_HISTORY_PATH = "chat/history"
CHAT_PAGE_PATH = "chat/"
CATALOG_SELLER_LINK_SELECTOR = (
    ".pseudo-a[data-href], .avatar-photo[data-href], .media-user-name a[href]"
)
CATALOG_SELLER_LINK_MISSING = "Catalog seller profile link is missing"
CATALOG_SELLER_NAME_MISSING = "Catalog seller name is missing"
CATALOG_PRICE_MISSING = "Catalog offer price is missing"
CATALOG_CURRENCY_MISSING = "Catalog offer currency is missing"
CATALOG_SELLER_MISSING = "Catalog seller is missing"
CATALOG_TRUE_FLAG = 1
CATALOG_INTERNAL_ATTRIBUTES = frozenset({"online", "auto", "user"})
USER_PROFILE_LINK_INVALID = "Invalid seller profile link"
USER_PROFILE_PATH = "users"
MAX_USER_ID_LENGTH = 20
