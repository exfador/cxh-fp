log_greeting_changed = (
    "$MAGENTA@{} (ID: {})$RESET changed the greeting text to $YELLOW{}$RESET."
)
log_greeting_cooldown_changed = "$MAGENTA@{} (ID: {})$RESET changed the cooldown of the welcome message to $YELLOW{}$RESET days."
log_order_confirm_changed = "$MAGENTA@{} (ID: {})$RESET changed the text of order confirmation reply to $YELLOW{}$RESET."
log_review_reply_changed = "$MAGENTA@{} (ID: {})$RESET changed the text of {}-star(s) review reply to $YELLOW{}$RESET."
log_param_changed = "$MAGENTA@{} (ID: {})$RESET changed value of $CYAN{}$RESET in $YELLOW[{}]$RESET section to $YELLOW{}$RESET."
log_notification_switched = "$MAGENTA@{} (ID: {})$RESET switched notifications $YELLOW{}$RESET for chat $YELLOW{}$RESET to $CYAN{}$RESET."
log_ad_linked = (
    "$MAGENTA@{} (ID: {})$RESET linked auto-delivery to lot $YELLOW{}$RESET."
)
log_ad_text_changed = '$MAGENTA@{} (ID: {})$RESET changed the delivery text of  $YELLOW{}$RESET to $YELLOW"{}"$RESET.'
log_ad_deleted = (
    "$MAGENTA@{} (ID: {})$RESET deleted auto-delivery from $YELLOW{}$RESET."
)
log_gf_created = (
    "$MAGENTA@{} (ID: {})$RESET created goods file $YELLOWstorage/products/{}$RESET."
)
log_gf_unlinked = "$MAGENTA@{} (ID: {})$RESET unlined goods file from $YELLOW{}$RESET."
log_gf_linked = "$MAGENTA@{} (ID: {})$RESET linked goods file $YELLOWstorage/products/{}$RESET to $YELLOW{}$RESET."
log_gf_created_and_linked = "$MAGENTA@{} (ID: {})$RESET created and linked goods file $YELLOWstorage/products/{}$RESET to $YELLOW{}$RESET."
log_gf_new_goods = "$MAGENTA@{} (ID: {})$RESET added $CYAN{}$RESET item(s) in $YELLOWstorage/products/{}$RESET."
log_gf_downloaded = "$MAGENTA@{} (ID: {})$RESET requested the goods file $YELLOWstorage/products/{}$RESET."
log_gf_deleted = "$MAGENTA@{} (ID: {})$RESET deleted the goods file $YELLOWstorage/products/{}$RESET."
log_ar_added = "$MAGENTA@{} (ID: {})$RESET added new command $YELLOW{}$RESET."
log_ar_response_text_changed = '$MAGENTA@{} (ID: {})$RESET response text of command $YELLOW{}$RESET to $YELLOW"{}"$RESET.'
log_ar_notification_text_changed = '$MAGENTA@{} (ID: {})$RESET notification text of command $YELLOW{}$RESET to $YELLOW"{}"$RESET.'
log_ar_cmd_deleted = "$MAGENTA@{} (ID: {})$RESET deleted the command $YELLOW{}$RESET."
log_cfg_downloaded = "$MAGENTA@{} (ID: {})$RESET requested config $YELLOW{}$RESET."
log_tmplt_added = (
    '$MAGENTA@{} (ID: {})$RESET added the answer template $YELLOW"{}"$RESET.'
)
log_tmplt_deleted = (
    '$MAGENTA@{} (ID: {})$RESET deleted the answer template $YELLOW"{}"$RESET.'
)
log_pl_activated = '$MAGENTA@{} (ID: {})$RESET activated the plugin $YELLOW"{}"$RESET.'
log_pl_deactivated = (
    '$MAGENTA@{} (ID: {})$RESET deactivated the plugin $YELLOW"{}"$RESET.'
)
log_pl_deleted = '$MAGENTA@{} (ID: {})$RESET deleted the plugin $YELLOW"{}"$RESET.'
log_pl_delete_handler_err = (
    'An error occurred when executing the $YELLOW"{}"$RESET plugin removal handler.'
)
log_new_msg = "$MAGENTA$RESET New message in chat with $YELLOW{} (CID: {}):"
log_sending_greetings = (
    "User $YELLOW{} (CID: {})$RESET wrote for the first time! Sending greetings..."
)
log_new_cmd = "Received the command $YELLOW{}$RESET in the chat with the user $YELLOW{} (CID: {})$RESET."
ntfc_new_order = "🧾 <b>New order</b>\n<code>{}</code>\n\nBuyer: <code>{}</code>\nAmount: <code>{}</code>\nOrder: <code>#{}</code>\n\n<i>{}</i>"
ntfc_new_order_not_in_cfg = (
    "ℹ️ Built-in auto delivery is not configured for this offer. "
    "Plugin delivery status is not checked in this notification."
)
ntfc_new_order_ad_disabled = "ℹ️ Auto delivery is off in Bot features."
ntfc_new_order_ad_disabled_for_lot = "ℹ️ Auto delivery is off for this offer."
ntfc_new_order_user_blocked = (
    "ℹ️ Delivery is blocked for this buyer by your blocklist rules."
)
ntfc_new_order_will_be_delivered = "📦 Products will be delivered automatically."
ntfc_new_review = "⭐ <b>New review · {}</b>\nOrder: <code>{}</code>\n\n<b>Buyer’s review</b>\n<code>{}</code>{}"
ntfc_review_reply_text = "<b>Your reply</b>\n<code>{}</code>"
crd_proxy_detected = "Proxy detected."
crd_checking_proxy = "Running proxy checks..."
crd_proxy_err = (
    "Failed to connect to the proxy. Make sure that the data is entered correctly."
)
crd_proxy_success = "Proxy verified successfully! IP address: $YELLOW{}$RESET."
crd_acc_get_timeout_err = "Failed to load account data: Timeout exceeded."
crd_acc_get_unexpected_err = (
    "An unexpected error occurred while retrieving account information."
)
crd_try_again_in_n_secs = "The next attempt is in {} seconds(-s)..."
crd_getting_profile_data = "Getting lots and categories data..."
crd_profile_get_timeout_err = "Failed to load account lots data: timeout exceeded."
crd_profile_get_unexpected_err = (
    "An unexpected error occurred while retrieving data about the account's lots."
)
crd_profile_get_too_many_attempts_err = "An error occurred while getting data about the lots of the account: the number of attempts ({}) was exceeded."
crd_profile_updated = "Updated the information about profile lots $YELLOW({})$RESET and categories $YELLOW({})$RESET."
crd_tg_profile_updated = "Updated the information about profile lots $YELLOW({})$RESET and categories $YELLOW({})$RESET (Telegram Control Panel)."
crd_raise_time_err = 'The $CYAN"{}"$RESET category lots could not be raised. FunPay says: "{}". Next attempt in {}.'
crd_raise_unexpected_err = 'An unexpected error occurred while trying to raise $CYAN"{}"$RESET catgory lots. Pause for 10 seconds.'
crd_raise_status_code_err = (
    'Error {} when raising lots of the $CYAN"{}"$RESET category. Pause for 1 minute...'
)
crd_lots_raised = 'All lots in the $CYAN"{}"$RESET category are raised!'
crd_raise_wait_3600 = "Next attempt in {}."
crd_msg_send_err = "An error occurred when sending a message to chat $YELLOW{}$RESET."
crd_msg_attempts_left = "Attempts left: $YELLOW{}$RESET."
crd_msg_no_more_attempts_err = (
    "Failed to send a message to chat $YELLOW{}$RESET: the number of attempts exceeded."
)
crd_msg_sent = "Sent a message to the chat $YELLOW{}."
crd_session_timeout_err = "Failed to refresh session: timeout exceeded."
crd_session_unexpected_err = (
    "An unexpected error occurred while refreshing the session."
)
crd_session_no_more_attempts_err = (
    "Failed to refresh session: the number of attempts was exceeded."
)
crd_session_updated = "Session updated."
crd_raise_loop_started = "$CYANThe auto-raise loop is running (this does not mean that auto-raise are enabled)."
crd_raise_loop_not_started = "$CYANThe auto-raise loop was not started because there are no lots detected on the account."
crd_session_loop_started = "$CYANThe session refresh loop is running."
crd_no_plugins_folder = "The plugins folder is not detected."
crd_no_plugins = "No plugins detected."
crd_plugin_load_err = "Failed to load plugin {}."
crd_plugin_handlers_err = (
    "Failed to register handlers of plugin {}. The plugin has been disabled."
)
crd_invalid_uuid = "Failed to load plugin {}: invalid UUID."
crd_uuid_already_registered = "UUID {} ({}) is already registered."
crd_handlers_registered = "The handlers from $YELLOW{}.py$RESET are registered."
crd_handler_err = "An error occurred in the handler's execution."
crd_tg_au_err = (
    "Failed to update the message with user information: {}. I will try without a link."
)
