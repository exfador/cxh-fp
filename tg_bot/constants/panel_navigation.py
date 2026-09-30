PANEL_CONTEXT_NAME = "cxh_panel_navigation"
PANEL_LOCK_COUNT = 64
PANEL_CALLBACK_PREFIX = "pback:"
PANEL_BUTTON_BACK = "gl_back"
PANEL_BUTTON_CANCEL = "gl_cancel"
PANEL_BUTTON_HOME = "menu_home_button"
PANEL_HOME_CALLBACK = "ops:home"
PANEL_STATE_NONCE = "nonce"
PANEL_EDIT_METHODS = frozenset({"send_message", "edit_message_text"})
PANEL_REPLACE_METHOD = "edit_message_reply_markup"
PANEL_REMOVE_METHOD = "delete_message"
PANEL_REPLACE_ACTIONS = frozenset({"switch", "switch_tg_notifications", "lang"})
PANEL_REPLACE_MENU_ACTIONS = frozenset(
    {"refresh_lots", "refresh_orders", "refresh_profile"}
)
