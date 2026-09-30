from types import MappingProxyType

from tg_bot import CBT

OPERATOR_PREFIX = "ops"
OPERATOR_CALLBACK_PARTS = frozenset({2, 3})
OPERATOR_CONFIRMATION_STATE = "operator_logs_confirmation"
OPERATOR_CONFIRMATION_SECONDS = 120
OPERATOR_CONFIRMATION_BYTES = 8
OPERATOR_LOGGER = "CoxerHubBot.telegram"
OPERATOR_FAILURE_LOG = "Operator action failed: action=%s error=%s"
OPERATOR_INPUT_HANDLERS = MappingProxyType(
    {
        CBT.CHANGE_GOLDEN_KEY: "change_cookie",
        CBT.EDIT_WATERMARK: "edit_watermark",
        CBT.MANUAL_AD_TEST: "manual_delivery_text",
    }
)
OPERATOR_ACTIONS = MappingProxyType(
    {
        "home": "operator_home",
        "service": "operator_service",
        "images": "operator_images",
        "chat_image": "operator_chat_image",
        "offer_image": "operator_offer_image",
        "restore_backup": "operator_restore_backup",
        "delivery_test": "operator_delivery_test",
        "change_key": "operator_change_key",
        "watermark": "operator_watermark",
        "watermark_brand": "operator_watermark_brand",
        "watermark_clear": "operator_watermark_clear",
        "logs_clear": "operator_logs_clear",
        "logs_clear_confirm": "operator_logs_clear_confirm",
        "system": "operator_system",
        "about": "operator_about",
        "refresh_profile": "operator_refresh_profile",
    }
)
