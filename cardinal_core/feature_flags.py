from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class FeatureFlags:
    @property
    def autoraise_enabled(self) -> bool:
        return self.MAIN_CFG["FunPay"].getboolean("autoRaise")

    @property
    def autoresponse_enabled(self) -> bool:
        return self.MAIN_CFG["FunPay"].getboolean("autoResponse")

    @property
    def autodelivery_enabled(self) -> bool:
        return self.MAIN_CFG["FunPay"].getboolean("autoDelivery")

    @property
    def multidelivery_enabled(self) -> bool:
        return self.MAIN_CFG["FunPay"].getboolean("multiDelivery")

    @property
    def autorestore_enabled(self) -> bool:
        return self.MAIN_CFG["FunPay"].getboolean("autoRestore")

    @property
    def autodisable_enabled(self) -> bool:
        return self.MAIN_CFG["FunPay"].getboolean("autoDisable")

    @property
    def old_mode_enabled(self) -> bool:
        return self.MAIN_CFG["FunPay"].getboolean("oldMsgGetMode")

    @property
    def keep_sent_messages_unread(self) -> bool:
        return self.MAIN_CFG["FunPay"].getboolean("keepSentMessagesUnread")

    @property
    def show_image_name(self) -> bool:
        return self.MAIN_CFG["NewMessageView"].getboolean("showImageName")

    @property
    def bl_delivery_enabled(self) -> bool:
        return self.MAIN_CFG["BlockList"].getboolean("blockDelivery")

    @property
    def bl_response_enabled(self) -> bool:
        return self.MAIN_CFG["BlockList"].getboolean("blockResponse")

    @property
    def bl_msg_notification_enabled(self) -> bool:
        return self.MAIN_CFG["BlockList"].getboolean("blockNewMessageNotification")

    @property
    def bl_order_notification_enabled(self) -> bool:
        return self.MAIN_CFG["BlockList"].getboolean("blockNewOrderNotification")

    @property
    def bl_cmd_notification_enabled(self) -> bool:
        return self.MAIN_CFG["BlockList"].getboolean("blockCommandNotification")

    @property
    def include_my_msg_enabled(self) -> bool:
        return self.MAIN_CFG["NewMessageView"].getboolean("includeMyMessages")

    @property
    def include_fp_msg_enabled(self) -> bool:
        return self.MAIN_CFG["NewMessageView"].getboolean("includeFPMessages")

    @property
    def include_bot_msg_enabled(self) -> bool:
        return self.MAIN_CFG["NewMessageView"].getboolean("includeBotMessages")

    @property
    def only_my_msg_enabled(self) -> bool:
        return self.MAIN_CFG["NewMessageView"].getboolean("notifyOnlyMyMessages")

    @property
    def only_fp_msg_enabled(self) -> bool:
        return self.MAIN_CFG["NewMessageView"].getboolean("notifyOnlyFPMessages")

    @property
    def only_bot_msg_enabled(self) -> bool:
        return self.MAIN_CFG["NewMessageView"].getboolean("notifyOnlyBotMessages")

    @property
    def block_tg_login(self) -> bool:
        return self.MAIN_CFG["Telegram"].getboolean("blockLogin")
