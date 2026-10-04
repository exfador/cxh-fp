lnk_updates = "Updates"
lnk_chat = "Chat"
an_an = "{} Announcements"
an_ad = "{} Advertisement"
ord_refund = "↩️ Refund order"
ord_open = "🧾 Open order"
ord_answer = "💬 Reply"
ord_templates = "📝 Templates"
msg_reply = "💬 Reply"
msg_reply2 = "💬 Reply"
msg_templates = "📝 Templates"
msg_more = "📋 History"
msg_open_chat = "🌐 Open chat"
access_denied = "🔐 <b>Sign in to your bot</b>\n\nUser: {}\nSend the password you chose during setup."
access_granted = "✅ You have access.\n\nOpen /menu to manage the bot. Set up notifications separately for each Telegram chat."
access_granted_notification = '🔐 <b>New user signed in</b>\n<a href="tg://user?id={1}">{0}</a> · ID <code>{1}</code>'
param_disabled = "This feature is off. Open Bot features in the main menu to enable it."
old_mode_help = "💬 <b>How messages are loaded</b>\n\n<b>Full history</b> loads all new messages with images and authors. It marks the FunPay chat as read.\n\n<b>Latest message only</b> keeps the chat unread, but may miss messages sent in quick succession. Images and authors may be unavailable.\n\nOpening chat history loads recent messages and marks that chat as read."
bot_started = "🦊 <b>CXH FP is starting</b>\n\nTelegram is ready. Connecting to FunPay…\nIf this takes longer than usual, choose Tools → Download log."
fpc_init = '🦊 <b>CXH FP · {}</b>\nConnected to FunPay.\n\nAccount: {} · {}\nBalance: {} RUB · {} USD · {} EUR\nActive orders: {}\n\n/menu — open your dashboard\nDeveloper: <a href="https://t.me/coxerhub">@coxerhub</a>'
create_test_ad_key = "🔑 <b>Delivery test key</b>\n\nEnter the exact name of the linked offer you want to test."
test_ad_key_created = "🔑 Delivery key created for <code>{}</code>.\n\nSend this command in the FunPay chat where you want to deliver the product. The key works once.\n\n<code>!автовыдача {}</code>"
about = '🦊 <b>CXH FP · {}</b>\n\nManage your FunPay offers, orders and delivery from Telegram.\nDeveloper: <a href="https://t.me/coxerhub">@coxerhub</a>'
sys_info = "📊 <b>System status</b>\n\n<b>CPU</b>\n{}\nBot usage: <code>{}%</code>\n\n<b>Memory</b>\nTotal: <code>{} MB</code>\nUsed: <code>{} MB</code>\nFree: <code>{} MB</code>\nBot usage: <code>{} MB</code>\n\n<b>Session</b>\nUptime: <code>{}</code>\nChat ID: <code>{}</code>"
act_blacklist = "🚫 <b>Block a user</b>\n\nSend their FunPay username."
already_blacklisted = "<code>{}</code> is already blocked."
user_blacklisted = "🚫 <code>{}</code> added to the blocklist."
act_unban = "🔓 <b>Unblock a user</b>\n\nSend their FunPay username."
not_blacklisted = "<code>{}</code> is not on the blocklist."
user_unbanned = "✅ <code>{}</code> removed from the blocklist."
blacklist_empty = "No blocked users."
act_proxy = "🌐 <b>Add a proxy</b>\n\nSend <code>login:password@ip:port</code>, or <code>ip:port</code> if no login is needed."
proxy_already_exists = "Proxy <code>{}</code> is already saved."
proxy_added = "✅ Proxy <u>{}</u> saved."
proxy_format = "Use <code>login:password@ip:port</code> or <code>ip:port</code>."
proxy_adding_error = "Could not add the proxy. Check the address and login details."
proxy_undeletable = (
    "This proxy is in use. Switch to another connection before deleting it."
)
act_edit_watermark = "📝 <b>Message signature</b>\n\nCurrent:{}\n\nChoose a button or send a custom signature.\nSend <code>-</code> to remove it."
watermark_changed = "✅ Message signature saved."
watermark_deleted = "Message signature removed."
watermark_error = "Could not use that signature. Try another text."
logfile_not_found = "No log file yet."
logfile_sending = "Preparing the log file…"
logfile_error = "Could not send the log file. Please try again."
logfile_deleted = "Removed {} old log file(s)."
update_no_tags = "Automatic updates are disabled."
update_lasted = "Automatic updates are disabled."
update_get_error = "Automatic updates are disabled."
update_available = "Automatic updates are disabled."
update_update = "Automatic updates are disabled."
update_backup = "📁 <b>Backup</b>\n\nSettings, storage and plugins. Includes access keys and products — keep this archive private."
update_backup_error = "Could not create a backup. Check free disk space and download the log from Tools → Download log."
update_backup_send_error = "Could not send the backup. Please try again."
update_backup_not_found = "No backup yet. Create one in Tools."
update_downloaded = "Automatic updates are disabled."
update_download_error = "Automatic updates are disabled."
update_done = "Automatic updates are disabled."
update_done_exe = "Automatic updates are disabled."
update_install_error = "Automatic updates are disabled."
send_backup = "📁 <b>Restore a backup</b>\n\nSend the backup ZIP. Matching settings and data files will be replaced."
restarting = "🔄 Restarting… The bot will reconnect when it is ready."
power_off_0 = "⏹ <b>Shut down the bot?</b>\n\nMessages and orders will no longer be processed. To resume, start the bot on your computer or server."
power_off_1 = "Confirm that you want to shut down the bot."
power_off_2 = "Start the bot on your computer or server to reconnect."
power_off_3 = "Choose Restart to apply saved settings."
power_off_4 = "Confirm that you want to shut down the bot."
power_off_5 = "Confirm that you want to shut down the bot."
power_off_6 = "⏹ Shutting down…"
power_off_cancelled = "Shutdown cancelled. The bot is still running."
power_off_error = "This confirmation has expired. Open the shutdown menu again."
enter_msg_text = "💬 <b>Reply to the buyer</b>\n\nSend your message."
msg_sent = '✅ Sent to <a href="https://funpay.com/chat/?node={}">{}</a>.'
msg_sent_short = "✅ Message sent."
msg_sending_error = 'Could not send the message to <a href="https://funpay.com/chat/?node={}">{}</a>. Please try again.'
msg_sending_error_short = "Could not send the message. Please try again."
send_img = "🖼 Send an image to upload to FunPay."
greeting_changed = "✅ Greeting saved."
greeting_cooldown_changed = (
    "✅ The same buyer can receive another greeting after {} days."
)
order_confirm_changed = "✅ After-sale message saved."
review_reply_changed = "✅ Reply saved for {} reviews."
review_reply_empty = (
    "⭐ <b>Review reply · {}</b>\n\nNo reply text yet. Add a message for this rating."
)
review_reply_text = "⭐ <b>Review reply · {}</b>\n\n<code>{}</code>"
get_chat_error = "Could not load this chat. Please try again."
viewing = "Viewing"
you = "You"
support = "Support"
photo = "Photo"
refund_attempt = (
    "Could not refund order <code>#{}</code>.\nAttempts remaining: <code>{}</code>."
)
refund_error = "Could not refund order <code>#{}</code>. Check the order on FunPay."
refund_complete = "✅ Order #{} refunded."
updating_profile = "Refreshing account details…"
profile_updating_error = "Could not refresh account details. Please try again."
act_change_golden_key = "🔑 <b>FunPay access key</b>\n\nSend your new golden_key."
cookie_changed = "✅ FunPay key saved{}."
cookie_changed2 = "\nChoose Tools → Restart to reconnect with the new key."
cookie_incorrect_format = (
    "That does not look like a golden_key. Copy the full value and try again."
)
cookie_error = "FunPay did not accept this key. Check that it is current and try again."
ad_lot_not_found_err = (
    "Offer <code>{}</code> is no longer in the list. Refresh it and select again."
)
ad_already_ad_err = "Delivery is already set up for <code>{}</code>."
ad_lot_already_exists = "<code>{}</code> already has delivery settings."
ad_lot_linked = "✅ Delivery linked to <code>{}</code>."
ad_link_gf = "📂 <b>Link a product file</b>\n\nSend the file name. A new file will be created if it does not exist.\nSend <code>-</code> to unlink the current file."
ad_gf_unlinked = "Product file unlinked from <code>{}</code>."
ad_gf_linked = "✅ Linked <code>storage/products/{}</code> to <code>{}</code>."
ad_gf_created_and_linked = (
    "✅ Created <code>storage/products/{}</code> and linked it to <code>{}</code>."
)
ad_creating_gf = "Creating <code>storage/products/{}</code>…"
ad_product_var_err = "<code>{}</code> has a product file, but its delivery message has no <code>$product</code>. Add this variable to include the product."
ad_product_var_err2 = (
    "Add <code>$product</code> to the delivery message before linking a product file."
)
ad_text_changed = "✅ Delivery message saved for <code>{}</code>.\n\n<code>{}</code>"
ad_updating_lots_list = "Refreshing offers and categories…"
ad_lots_list_updating_err = "Could not refresh offers. Please try again."
gf_not_found_err = "Product file <code>{}</code> is no longer in the list. Refresh it and select again."
copy_lot_name = "📦 Send the offer name exactly as it appears on FunPay."
act_create_gf = (
    "📂 <b>New product file</b>\n\nSend a file name without the .txt extension."
)
gf_name_invalid = "Use English or Russian letters, digits, spaces, <code>_</code> or <code>-</code> in the file name."
gf_already_exists_err = "Product file <code>{}</code> already exists."
gf_creation_err = (
    "Could not create <code>{}</code>. Check the file name and folder permissions."
)
gf_created = "✅ Created <code>storage/products/{}</code>."
gf_amount = "Products in stock"
gf_uses = "Linked offers"
gf_send_new_goods = "📦 <b>Add products</b>\n\nSend one product per line. Use <code>Shift+Enter</code> for a new line."
gf_add_goods_err = "Could not add the products. Please try again."
gf_new_goods = (
    "✅ Added <code>{}</code> product(s) to <code>storage/products/{}</code>."
)
gf_empty_error = "No products in storage/products/{}."
gf_linked_err = "<code>storage/products/{}</code> is still linked to offers. Unlink it from each offer before deleting it."
gf_deleting_err = (
    "Could not delete <code>storage/products/{}</code>. Check folder permissions."
)

ntfc_new_order_not_paid = "Delivery skipped: the order is not in Paid status."
