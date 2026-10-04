CONNECTION_CHECK_SECONDS = 30
CONNECTION_DOWN_SECONDS = 300
CONNECTION_AUTH_SECONDS = 120
CONNECTION_THREAD_NAME = "cxh-connection-monitor"
CONNECTION_LOGGER = "CoxerHubBot.connection"
CONNECTION_TIME_FORMAT = "%H:%M"
CONNECTION_DATE_FORMAT = "%d.%m %H:%M"
CONNECTION_REASONS = {
    "network": "conn_reason_network",
    "server": "conn_reason_server",
    "stalled": "conn_reason_stalled",
    "other": "conn_reason_other",
}
