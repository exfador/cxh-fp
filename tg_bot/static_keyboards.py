from telebot.types import InlineKeyboardMarkup as K
from tg_bot.keyboard_views.styled_button import StyledButton as B
from tg_bot.constants.button_styles import BUTTON_PRIMARY
from tg_bot.constants.configuration import CONFIGURATION_ROWS
from tg_bot import CBT
from locales.localizer import Localizer

localizer = Localizer()
_ = localizer.translate


def CLEAR_STATE_BTN() -> K:
    return K().add(B(_("gl_cancel"), callback_data=CBT.CLEAR_STATE))


def REFRESH_BTN() -> K:
    return K().add(B(_("gl_refresh"), callback_data=CBT.UPDATE_PROFILE))


def SETTINGS_SECTIONS() -> K:
    return (
        K()
        .row(
            B(
                _("mm_global"),
                callback_data=f"{CBT.CATEGORY}:main",
                style=BUTTON_PRIMARY,
            ),
            B(_("mm_notifications"), callback_data=f"{CBT.CATEGORY}:tg"),
        )
        .row(
            B(_("mm_autodelivery"), callback_data=f"{CBT.CATEGORY}:ad"),
            B(_("mm_autoresponse"), callback_data=f"{CBT.CATEGORY}:ar"),
        )
        .row(
            B(_("mm_plugins"), callback_data=f"{CBT.PLUGINS_LIST}:0"),
            B(_("mm_templates"), callback_data=f"{CBT.TMPLT_LIST}:0"),
        )
        .add(B(_("mm_language"), callback_data=f"{CBT.CATEGORY}:lang"))
        .add(B(_("gl_next"), callback_data=CBT.MAIN2))
    )


def SETTINGS_SECTIONS_2() -> K:
    return (
        K()
        .row(
            B(_("mm_greetings"), callback_data=f"{CBT.CATEGORY}:gr"),
            B(_("mm_order_confirm"), callback_data=f"{CBT.CATEGORY}:oc"),
        )
        .row(
            B(_("mm_review_reply"), callback_data=f"{CBT.CATEGORY}:rr"),
            B(_("mm_new_msg_view"), callback_data=f"{CBT.CATEGORY}:mv"),
        )
        .row(
            B(_("mm_blacklist"), callback_data=f"{CBT.CATEGORY}:bl"),
            B(_("mm_configs"), callback_data=CBT.CONFIG_LOADER),
        )
        .row(
            B(
                _("mm_authorized_users"),
                callback_data=f"{CBT.AUTHORIZED_USERS}:0",
                style=BUTTON_PRIMARY,
            ),
            B(_("mm_proxy"), callback_data=f"{CBT.PROXY}:0"),
        )
        .add(B(_("gl_back"), callback_data=CBT.MAIN))
    )


def AR_SETTINGS() -> K:
    return (
        K()
        .row(
            B(_("ar_edit_commands"), callback_data=f"{CBT.CMD_LIST}:0"),
            B(_("ar_add_command"), callback_data=CBT.ADD_CMD, style=BUTTON_PRIMARY),
        )
        .row(B(_("gl_back"), callback_data=CBT.MAIN))
    )


def AD_SETTINGS() -> K:
    from tg_bot.keyboard_views.operator import operator_button

    kb = K().row(
        B(_("ad_edit_autodelivery"), callback_data=f"{CBT.AD_LOTS_LIST}:0"),
        B(
            _("ad_add_autodelivery"),
            callback_data=f"{CBT.FP_LOTS_LIST}:0",
            style=BUTTON_PRIMARY,
        ),
    )
    kb.row(B(_("ad_edit_goods_file"), callback_data=f"{CBT.PRODUCTS_FILES_LIST}:0"))
    kb.row(
        B(_("ad_upload_goods_file"), callback_data=CBT.UPLOAD_PRODUCTS_FILE),
        B(_("ad_create_goods_file"), callback_data=CBT.CREATE_PRODUCTS_FILE),
    )
    kb.row(operator_button("operator_delivery_test", "delivery_test"))
    return kb.row(B(_("gl_back"), callback_data=CBT.MAIN))


def CONFIGS_UPLOADER() -> K:
    kb = K()
    for download_label, upload_label, download, upload in CONFIGURATION_ROWS:
        kb.row(
            B(_(download_label), callback_data=download),
            B(_(upload_label), callback_data=upload),
        )
    return kb.row(B(_("gl_back"), callback_data=CBT.MAIN2))


def UPLOAD_PLUGIN() -> K:
    return K().add(B(_("gl_cancel"), callback_data=CBT.CLEAR_STATE))
