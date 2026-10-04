mm_chat_sync = "💬 Chat sync"
cs_panel_title = "💬 <b>Chat sync</b>"
cs_panel_unbound = (
    "Every FunPay chat gets its own topic in a Telegram group. Buyer messages arrive "
    "in the topic, and your reply in the topic goes to the buyer.\n\n"
    "<b>How to connect</b>\n"
    "1. Create a group and turn on Topics in its settings.\n"
    "2. Add @{} to the group and make it an admin with the Manage topics right. "
    "The button below asks for the right permissions.\n"
    "3. The bot links the group by itself. If it does not, send /{} in the group."
)
cs_panel_group = "Group: <b>{}</b> (<code>{}</code>)"
cs_panel_ok = "Status: ✅ working"
cs_panel_problems = "Status: ⚠️ needs fixing"
cs_panel_topics = "Linked topics: {}"
cs_panel_syncing = "⏳ Creating topics for recent chats…"
cs_panel_usage = (
    "Reply in a chat topic and the message goes to the buyer. Photos, images and "
    "stickers are sent too. In a topic, /{} shows recent messages and the "
    "«📝 Templates» button sends a saved reply."
)
cs_problem_unreachable = "the bot cannot see the group: add it back"
cs_problem_topics = "topics are off in the group: turn on Topics in the group settings"
cs_problem_admin = "the bot is not a group admin"
cs_problem_topics_right = "the bot lacks the Manage topics right"
cs_problem_old_mode = (
    "«Latest message only» is on: turn it off in "
    "«Automation → Bot features», otherwise messages will not reach the topics"
)
cs_opt_own = "My messages from the FunPay site"
cs_opt_bot = "Bot messages and auto replies"
cs_opt_ads = "FunPay promotional messages"
cs_opt_watermark = "Hide the bot signature"
cs_sync_button = "🧵 Create topics for recent chats"
cs_unbind_button = "🔌 Unlink group"
cs_add_bot_button = "➕ Add the bot to a group"
cs_unbind_confirm = (
    "Unlink the group? Links between topics and FunPay chats will be reset. "
    "The topics and messages stay in the group."
)
cs_unbind_yes = "Yes, unlink"
cs_unbind_no = "Keep it"
cs_unbound_done = "Group unlinked"
cs_sync_started = "Creating topics, this takes a few minutes"
cs_sync_running = "Topics are already being created"
cs_bound = (
    "✅ The group is linked to CXH FP.\n\n"
    "Every FunPay chat gets its own topic. Write in a topic and the message goes "
    "to the buyer. Creating topics for recent chats now."
)
cs_already_bound = "✅ This group is already linked to chat sync."
cs_other_bound = (
    "Chat sync is linked to another group. To move it here, send /{} in this group."
)
cs_bind_problems = "⚠️ Cannot link the group yet:\n{}\n\nFix it and send /{}."
cs_need_admin = (
    "Make me an admin with the Manage topics right and I will link the group."
)
cs_need_topics = "To sync chats, turn on Topics in the group settings, then send /{}."
cs_topic_header = (
    '💬 <b>{}</b>\n<a href="{}">Chat</a> · <a href="{}">Sales</a> · '
    '<a href="{}">Purchases</a>\n\nWrite in this topic to reply in the FunPay chat.'
)
cs_open_chat = "💬 Open the chat on FunPay"
cs_history_button = "📜 History"
cs_templates_button = "📝 Templates"
cs_close = "✖️ Close"
cs_history_loading = "Loading history…"
cs_history_empty = "The chat history is empty."
cs_history_failed = "❌ Could not load the chat history."
cs_no_templates = "There are no reply templates. Add them in the Templates menu."
cs_templates_title = "📝 Pick a template; it is sent to the buyer right away."
cs_template_sent = "📝 Template sent:\n{}"
cs_send_failed = "❌ Could not send to FunPay."
cs_media_sticker = (
    "❌ Could not turn this sticker into an image, and FunPay accepts only images."
)
cs_media_document = "❌ FunPay accepts only image files."
cs_media_size = "❌ The file is larger than 20 MB."
cs_topic_unknown = "This topic is not linked to a FunPay chat"
cs_sent_short = "✅ Sent"
cs_failed_short = "❌ Not sent"
cs_helpers_button = "🤖 Helper bots: {}"
cs_helpers_title = "🤖 <b>Helper bots</b>"
cs_helpers_about = (
    "Telegram lets one bot send about 20 messages a minute to a group. Helpers take "
    "part of the sending: they forward buyer messages, create topics and change their "
    "icons. Your replies, buttons and menus stay with the main bot."
)
cs_helpers_speed = "Bots now: {}, up to {} messages a minute."
cs_helpers_empty = "No helpers yet."
cs_helpers_howto = (
    "<b>How to add</b>\n"
    "1. Send /newbot to @BotFather and create a bot.\n"
    "2. Tap «➕ Add helper» and send the token. "
    "The bot deletes the message with the token right away.\n"
    "3. Add the helper to the group as an admin with the Manage topics right: "
    "use the «➕ to group» button next to it."
)
cs_helper_status_ok = "✅ working"
cs_helper_status_send = "⚠️ forwards only, lacks the Manage topics right"
cs_helper_status_missing = "❌ not in the group"
cs_helper_status_token = "❌ invalid token"
cs_helper_status_unbound = "⏸ no group linked"
cs_helper_add_button = "➕ Add helper"
cs_helper_to_group = "➕ @{} to group"
cs_helper_remove = "🗑 @{}"
cs_helper_back = "🤖 Back to helpers"
cs_helper_prompt = (
    "Send the helper bot token from @BotFather. I will delete that message right away."
)
cs_helper_added = (
    "✅ Helper @{} added. Now add it to the group as an admin with the "
    "Manage topics right."
)
cs_helper_bad_token = "❌ This is not a bot token, or Telegram rejected it."
cs_helper_is_main = "❌ This is the main bot; there is no need to add it."
cs_helper_exists = "❌ This bot is already added."
cs_helper_limit = "❌ You can add at most {} helpers."
cs_helper_check_failed = "❌ Could not check the token, try again."
cs_helper_removed = "Helper removed"
cs_helper_description = (
    "CXH FP chat sync helper bot. Manage it from the store's main bot."
)
