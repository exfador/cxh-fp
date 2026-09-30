ar_cmd_not_found_err = (
    "Command <code>{}</code> is no longer in the list. Refresh it and select again."
)
ar_subcmd_duplicate_err = (
    "<code>{}</code> appears more than once. Keep one copy of each command."
)
ar_cmd_already_exists_err = "<code>{}</code> already exists. Open it to edit its reply."
ar_enter_new_cmd = "💬 <b>New command</b>\n\nEnter the text a buyer should send. Separate aliases with <code>|</code>, for example <code>!help | !info</code>.\n\nUse the Cancel button to leave this step."
ar_cmd_added = "✅ Command added: <code>{}</code>."
ar_response_text = "Buyer reply"
ar_notification_text = "Telegram notification"
ar_response_text_changed = "✅ Reply saved for <code>{}</code>.\n\n<code>{}</code>"
ar_notification_text_changed = (
    "✅ Notification saved for <code>{}</code>.\n\n<code>{}</code>"
)
cfg_main = "📁 <b>Main settings</b>\n\nContains access keys and the bot password. Keep this file private."
cfg_ar = "💬 <b>Auto reply settings</b>\nCommands, replies and notification texts."
cfg_ad = (
    "📦 <b>Delivery settings</b>\nLinked offers, delivery texts and product file names."
)
cfg_not_found_err = "Configuration file {} was not found."
cfg_empty_err = "Configuration file {} is empty."
tmplt_not_found_err = (
    "Template <code>{}</code> is no longer in the list. Refresh it and select again."
)
tmplt_already_exists_err = "This text is already saved as a template."
tmplt_added = "✅ Template saved."
tmplt_msg_sent = (
    '✅ Sent to <a href="https://funpay.com/chat/?node={}">{}</a>.\n\n<code>{}</code>'
)
pl_not_found_err = "Plugin <code>{}</code> is no longer available. Refresh the list."
pl_file_not_found_err = "Plugin file <code>{}</code> was not found.\nChoose Tools → Restart to reload the plugin list."
pl_commands_list = "💬 <b>{} · Commands</b>"
pl_author = "Developer"
plugin_details_text = (
    "🧩 <b>{0} · {1}</b>\n\n{2}\n\nDeveloper: {3}\nPlugin ID: <code>{4}</code>"
)
pl_new = "🧩 <b>Upload a plugin</b>\n\nSend a <code>.py</code> file or a <code>.zip</code> archive up to 20 MB.\n\nThe ZIP must contain one plugin <code>.py</code> file and its dependency folders. A single enclosing folder is supported. Everything is installed in <code>plugins</code>. Repack RAR archives as ZIP first.\n\nExisting files are kept. Restart the bot from Tools after installation.\n\nPlugins can access bot data. Only upload trusted plugins."
au_user_settings = "🔐 <b>Access · {}</b>"
adv_fpc = ""
adv_description = ""
desc_main = "🦊 <b>CXH FP · 1.1</b>\n\nChoose what to manage."
desc_lang = "🌐 <b>Language</b>\n\nChoose the language for bot menus and messages."
desc_gs = "⚙️ <b>Bot features</b>\n\nTurn features on or off. Delivery and replies also have settings for individual offers and commands."
desc_ns = "🔔 <b>Notifications</b>\n\nChoose what the bot sends to this Telegram chat.\nChat ID: <code>{}</code>"
desc_bl = "🚫 <b>Blocklist rules</b>\n\nChoose which actions to block for users on your list.\n\nAdd — block a user.\nRemove — lift their restrictions.\nList — view blocked users."
desc_ar = "💬 <b>Auto replies</b>\n\nSet up replies to buyer commands. Each command can also send you a Telegram notification."
desc_ar_list = (
    "💬 <b>Commands</b>\n\nSelect a command to edit its reply or notification."
)
desc_ad = "📦 <b>Delivery</b>\n\nLink offers to product files and choose the message buyers receive."
desc_ad_list = "📦 <b>Linked offers</b>\n\nSelect an offer to edit its delivery message, product file and rules."
desc_ad_fp_lot_list = "📦 <b>Choose an offer</b>\n\nSelect an offer to link delivery. Refresh the list if it is missing.\n\nLast refreshed: {}"
desc_gf = "📂 <b>Product files</b>\n\nSelect a file to view stock, add products or download it."
desc_mv = "💬 <b>Message display</b>\n\nChoose which messages appear in chat notifications and when an alert is sent."
desc_gr = "👋 <b>Greetings</b>\n\nChoose who receives a greeting and how often.\n\n<b>Current message</b>\n<code>{}</code>"
desc_oc = "✅ <b>After a sale</b>\n\nMessage sent when a buyer confirms an order.\n\n<b>Current message</b>\n<code>{}</code>"
desc_or = "⭐ <b>Review replies</b>\n\nSelect a rating to preview its reply. Use «Text» to edit it and «Auto reply» to turn it on or off. Each rating has its own reply."
desc_an = "External broadcasts are disabled."
desc_cfg = "📁 <b>Configuration files</b>\n\nDownload current settings or upload a replacement file."
desc_tmplt = "📝 <b>Reply templates</b>\n\nKeep frequently used messages here and select them when replying to buyers."
desc_pl = "🧩 <b>Plugins</b>\n\nSelect a plugin to view its details and settings. Restart the bot after changing plugins."
desc_au = "🔐 <b>Bot access</b>\n\nThese users can manage the bot. Select a user to view their access settings."
desc_proxy = "🌐 <b>Proxy connection</b>\n\nChoose a saved proxy or add one."
cmd_menu = "Main menu"
cmd_language = "Choose interface language"
cmd_profile = "Account and balance"
cmd_golden_key = "Change FunPay access key"
cmd_test_lot = "Create a delivery test key"
cmd_upload_chat_img = "Upload a chat image"
cmd_upload_offer_img = "Upload an offer image"
cmd_upload_plugin = "Upload a plugin"
cmd_ban = "Block a FunPay user"
cmd_unban = "Unblock a FunPay user"
cmd_black_list = "View blocked users"
cmd_watermark = "Change bot message signature"
cmd_logs = "Download log"
cmd_del_logs = "Remove old log archives"
cmd_about = "Version and developer"
cmd_check_updates = "Automatic updates are disabled"
cmd_update = "Automatic updates are disabled"
cmd_sys = "Process status"
cmd_create_backup = "Create a backup"
cmd_get_backup = "Download the latest backup"
cmd_upload_backup = "Restore a backup"
cmd_restart = "Restart the bot"
cmd_power_off = "Shut down the bot"
v_edit_greeting_text = "👋 <b>Greeting text</b>\n\nSend the message buyers should receive when they contact you."
v_edit_greeting_cooldown = "⏱ <b>Greeting interval</b>\n\nEnter the number of days before the same buyer can receive another greeting."
v_edit_order_confirm_text = "✅ <b>After-sale message</b>\n\nSend the message buyers should receive after confirming an order."
v_edit_review_reply_text = (
    "⭐ <b>Review reply · {}</b>\n\nSend the reply for this rating."
)
v_edit_delivery_text = "📦 <b>Delivery message</b>\n\nSend the text buyers should receive with their order."
v_edit_response_text = (
    "💬 <b>Command reply</b>\n\nSend the text buyers should receive for this command."
)
v_edit_notification_text = "🔔 <b>Command notification</b>\n\nSend the text you want to receive in Telegram when a buyer uses this command."
V_new_template = (
    "📝 <b>New template</b>\n\nSend the message you want to save for future replies."
)
v_list = "Available variables"
v_date = "<code>$date</code> — current date: <i>DD.MM.YYYY</i>."
v_date_text = "<code>$date_text</code> — current date: <i>January 1</i>."
v_full_date_text = (
    "<code>$full_date_text</code> — current date: <i>January 1, 2020</i>."
)
v_time = "<code>$time</code> — current time: <i>HH:MM</i>."
v_full_time = "<code>$full_time</code> — current time: <i>HH:MM:SS</i>."
v_photo = "<code>$photo=[PHOTO ID]</code> — insert an image. Replace <code>[PHOTO ID]</code> with the ID from Tools → Images."
v_sleep = "<code>$sleep=[TIME]</code> — pause before continuing. Replace <code>[TIME]</code> with a delay in seconds."
v_order_id = "<code>$order_id</code> — order ID, without #."
v_order_link = "<code>$order_link</code> — link to the order."
v_order_title = "<code>$order_title</code> — order title."
v_order_params = "<code>$order_params</code> — order options."
v_order_desc_and_params = "<code>$order_desc_and_params</code> — title and options, or whichever is available."
v_order_desc_or_params = "<code>$order_desc_or_params</code> — title; uses order options if the title is empty."
v_game = "<code>$game</code> — game name."
v_category = "<code>$category</code> — subcategory name."
v_category_fullname = "<code>$category_fullname</code> — subcategory and game name."
v_product = (
    "<code>$product</code> — products from the linked file. Requires a product file."
)
v_chat_id = "<code>$chat_id</code> — FunPay chat ID."
v_chat_name = "<code>$chat_name</code> — FunPay chat name."
v_message_text = "<code>$message_text</code> — the other person’s message."
v_username = "<code>$username</code> — the other person’s username."
exc_param_not_found = 'Setting "{}" was not found.'
exc_param_cant_be_empty = 'Setting "{}" cannot be empty.'
exc_param_value_invalid = 'Invalid value for "{}". Allowed: {}. Received: "{}".'
exc_goods_file_not_found = 'Product file "{}" was not found.'
exc_goods_file_is_empty = 'Product file "{}" has no products.'
exc_not_enough_items = 'Not enough products in "{}". Needed: {}. Available: {}.'
exc_no_product_var = (
    '"productsFileName" is set, but "response" does not include $product.'
)
exc_no_section = "Configuration section was not found."
exc_section_duplicate = "The configuration contains a duplicate section."
exc_cmd_duplicate = 'Command or alias "{}" already exists.'
exc_cfg_parse_err = "Configuration error in {}, section [{}]: {}"
exc_plugin_field_not_found = (
    'Could not load plugin "{}": required field "{}" is missing.'
)
log_tg_initialized = "$MAGENTATelegram bot initialized."
log_tg_started = "$CYANTelegram bot $YELLOW@{}$CYAN started."
log_tg_handler_error = "An error occurred while executing the Telegram bot handler."
log_tg_update_error = "An error ({}) occurred while getting Telegram updates (probably an invalid token?)."
log_tg_notification_error = (
    "An error occurred while sending a notification to chat $YELLOW{}$RESET."
)
log_access_attempt = "Access denied: user={} id={}."
log_click_attempt = "Unauthorized callback: user={} id={} chat={} chat_id={}."
log_access_granted = "$MAGENTA@{} (ID: {})$RESET gained access to the control panel."
log_new_ad_key = "Delivery key created: user={0} id={1} lot={2}."
log_user_blacklisted = "$MAGENTA@{} (ID: {})$RESET has blacklisted $YELLOW{}$RESET."
log_user_unbanned = (
    "$MAGENTA@{} (ID: {})$RESET has removed $YELLOW{}$RESET from the blacklist."
)
log_watermark_changed = (
    "$MAGENTA@{} (ID: {})$RESET changed the message watermark to $YELLOW{}$RESET."
)
log_watermark_deleted = "$MAGENTA@{} (ID: {})$RESET deleted the message watermark."
