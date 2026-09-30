from tg_bot import CBT

CONFIGURATION_ROWS = (
    (
        "cfg_download_main",
        "cfg_upload_main",
        f"{CBT.DOWNLOAD_CFG}:main",
        "upload_main_config",
    ),
    (
        "cfg_download_ar",
        "cfg_upload_ar",
        f"{CBT.DOWNLOAD_CFG}:autoResponse",
        "upload_auto_response_config",
    ),
    (
        "cfg_download_ad",
        "cfg_upload_ad",
        f"{CBT.DOWNLOAD_CFG}:autoDelivery",
        "upload_auto_delivery_config",
    ),
)
