STATE_ENABLED = "🟢"
STATE_DISABLED = "⚪"
NOTIFICATION_ENABLED = "🔔"
NOTIFICATION_DISABLED = "🔕"
REVIEW_RATINGS = (1, 2, 3, 4, 5)
REVIEW_ENABLED = "✓"
REVIEW_DISABLED = "—"
SETTINGS_HELP_LABEL = "❔"

MAIN_SETTINGS_ROWS = (
    (("autoRaise", "gs_autoraise"), ("autoResponse", "gs_autoresponse")),
    (("autoDelivery", "gs_autodelivery"), ("multiDelivery", "gs_nultidelivery")),
    (("autoRestore", "gs_autorestore"), ("autoDisable", "gs_autodisable")),
)
MESSAGE_SETTINGS_ROWS = (
    (("includeMyMessages", "mv_incl_my_msg"),),
    (("notifyOnlyMyMessages", "mv_only_my_msg"),),
    (("includeFPMessages", "mv_incl_fp_msg"),),
    (("notifyOnlyFPMessages", "mv_only_fp_msg"),),
    (("includeBotMessages", "mv_incl_bot_msg"),),
    (("notifyOnlyBotMessages", "mv_only_bot_msg"),),
    (("showImageName", "mv_show_image_name"),),
)
GREETING_SETTINGS_ROWS = (
    (("sendGreetings", "gr_greetings"),),
    (("onlyNewChats", "gr_only_new_chats"),),
    (("ignoreSystemMessages", "gr_ignore_sys_msgs"),),
)
ORDER_SETTINGS_ROWS = (
    (("sendReply", "oc_send_reply"),),
    (("watermark", "oc_watermark"),),
)
BLACKLIST_SETTINGS_ROWS = (
    (("blockDelivery", "bl_autodelivery"),),
    (("blockResponse", "bl_autoresponse"),),
    (("blockNewMessageNotification", "bl_new_msg_notifications"),),
    (("blockNewOrderNotification", "bl_new_order_notifications"),),
    (("blockCommandNotification", "bl_command_notifications"),),
)
NOTIFICATION_SETTINGS_ROWS = (
    (("new_message", "ns_new_msg"), ("command", "ns_cmd")),
    (("new_order", "ns_new_order"), ("order_confirmed", "ns_order_confirmed")),
    (("review", "ns_new_review"), ("bot_start", "ns_bot_start")),
    (("lots_restore", "ns_lot_activate"), ("lots_deactivate", "ns_lot_deactivate")),
    (("delivery", "ns_delivery"), ("lots_raise", "ns_raise")),
    (("other", "ns_other"), ("connection", "ns_connection")),
)
