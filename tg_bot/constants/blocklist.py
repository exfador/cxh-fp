from types import MappingProxyType

BLOCKLIST_INPUT_STATE = "blocklist_input"
BLOCKLIST_CONFIRM_STATE = "blocklist_confirmation"
BLOCKLIST_INPUT_SECONDS = 900
BLOCKLIST_CONFIRM_SECONDS = 120
BLOCKLIST_NAME_LENGTH = 64
BLOCKLIST_HASH_LENGTH = 16
BLOCKLIST_LABEL_LENGTH = 40
BLOCKLIST_CALLBACK_HANDLERS = MappingProxyType(
    {
        "bl_list": "blocklist_list",
        "bl_add": "blocklist_add",
        "bl_remove": "blocklist_remove",
        "bl_select": "blocklist_select",
        "bl_confirm": "blocklist_confirm",
    }
)
