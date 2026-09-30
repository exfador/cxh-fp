from tg_bot.utils import NotificationTypes

DISABLED_NOTIFICATION_TYPES = frozenset(
    {
        NotificationTypes.announcement,
        NotificationTypes.ad,
        NotificationTypes.important_announcement,
    }
)
