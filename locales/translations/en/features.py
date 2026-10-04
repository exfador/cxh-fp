ns_connection = "{} FunPay connection"
conn_down = (
    "⚠️ <b>No connection to FunPay</b>\n\n"
    "For {} already, since {}. {}\n\n"
    "The bot keeps retrying and will tell you when the connection is back."
)
conn_reason_network = "The internet seems to be down, or funpay.com is unreachable."
conn_reason_server = "FunPay responds with a server error."
conn_reason_stalled = "The bot stopped receiving events from FunPay."
conn_reason_other = "Requests to FunPay fail; see the log for details."
conn_auth = (
    "🔑 <b>FunPay rejects the account</b>\n\n"
    "Since {} FunPay has been rejecting the bot's requests. Most likely the "
    "golden_key no longer works: you logged out on the site or changed the password.\n\n"
    "Send a new key with the button below and the bot will continue."
)
conn_restored = "✅ <b>FunPay connection restored</b>\n\nOutage: {}, from {} to {}."
menu_stats_button = "📈 Statistics"
menu_stats_title = "📈 <b>Sales statistics</b>"
menu_stats_loading = "📈 <b>Sales statistics</b>\n\n⏳ Loading sales for 30 days…"
menu_stats_empty = "There were no sales in the last 30 days."
menu_stats_periods = (
    "<b>Sold</b> (refunds excluded)\n"
    "<blockquote>Today: <b>{}</b> · {}\n"
    "7 days: <b>{}</b> · {}\n"
    "30 days: <b>{}</b> · {}</blockquote>"
)
menu_stats_month = (
    "<b>Last 30 days</b>\n"
    "✅ Completed: {} · {}\n"
    "⏳ Awaiting confirmation: {} · {}\n"
    "↩️ Refunds: {} · {}\n"
    "💳 Average order: {}"
)
menu_stats_top = "<b>🏆 Top categories</b>\n{}"
menu_stats_top_row = "{}. {} — {} · {}"
menu_stats_footer = "<i>Amounts as shown in the FunPay sales list. Updated at {}.</i>"
menu_stats_partial = "<i>Only the last {} orders are counted.</i>"
menu_stats_decimal = "."
order_card_title = "🧾 <b>Order #{}</b>"
order_card_block = "{}\n👤 Buyer: <b>{}</b>\n💰 Amount: <b>{}</b>\n🕒 Date: {}"
order_card_item = "📦 <b>{}</b>\n{}"
order_card_amount = "Quantity: {}"
order_card_review = "Review: {}"
order_card_offline = (
    "<i>Could not load details from FunPay right now; showing data from the list.</i>"
)
order_status_paid = "🟡 Paid, awaiting confirmation"
order_status_closed = "✅ Completed"
order_status_refunded = "↩️ Refunded"
order_open_button = "🔗 Open the order on FunPay"
mm_confirm_reminder = "⏰ Confirmation reminder"
cr_panel_title = "⏰ <b>Confirmation reminder</b>"
cr_panel_about = (
    "If a buyer paid, you replied, and the buyer stays silent for {} h without "
    "confirming the order, the bot sends one polite reminder. Each order gets at "
    "most one reminder, and none is sent if the buyer wrote last."
)
cr_panel_state = "State: {}"
cr_state_on = "🟢 on"
cr_state_off = "🔴 off"
cr_panel_hours = "Remind after: <b>{} h</b> since your last message"
cr_panel_sent = "Sent in 7 days: {}"
cr_problem_old_mode = (
    "«Latest message only» is on: the bot cannot see the conversation and cannot "
    "send reminders. Turn it off in «Automation → Bot features»."
)
cr_text_default = "<b>Text</b> (default)"
cr_text_custom = "<b>Text</b> (yours)"
cr_variables = (
    "<code>{}</code> is the buyer's username, <code>{}</code> the order number."
)
cr_toggle_on = "🟢 Reminder on"
cr_toggle_off = "🔴 Reminder off"
cr_hours_button = "⏱ After {} h"
cr_text_button = "📝 Edit text"
cr_reset_button = "↩️ Restore default text"
cr_text_reset_done = "Default text restored"
cr_hours_prompt = (
    "⏱ How many hours after your last message should the bot remind? "
    "Send a number from {} to {}."
)
cr_hours_invalid = "❌ Send a whole number of hours from {} to {}. Try again."
cr_hours_saved = "✅ Done: the bot will remind {} h after your last message."
cr_text_prompt = (
    "📝 Send the reminder text, up to {} characters.\n\n"
    "<code>$username</code> becomes the buyer's username, "
    "<code>$order_id</code> the order number."
)
cr_text_invalid = (
    "❌ The text must not be empty or longer than {} characters. Try again."
)
cr_text_saved = "✅ Reminder text saved."
cr_default_text = (
    "Hello, $username! If you have received order $order_id and everything is fine, "
    "please confirm it on FunPay. Thank you for your purchase!"
)
