from pathlib import Path

PLUGIN_DIRECTORY = Path("plugins")
MAX_PLUGIN_BYTES = 8 * 1024 * 1024
PLUGIN_FIELDS = (
    "NAME",
    "VERSION",
    "DESCRIPTION",
    "CREDITS",
    "SETTINGS_PAGE",
    "UUID",
    "BIND_TO_DELETE",
)
PLACEHOLDER_FLAG = "_cardinal_disabled_placeholder"
