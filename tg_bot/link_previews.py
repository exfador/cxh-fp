from telebot import types

from tg_bot.constants.link_previews import (
    LEGACY_PREVIEW_PARAMETER,
    PREVIEW_OPTIONS_PARAMETER,
    LINK_PREVIEWS_DISABLED,
)


def disable_link_previews(bound):
    parameters = bound.signature.parameters
    if PREVIEW_OPTIONS_PARAMETER in parameters:
        bound.arguments.pop(LEGACY_PREVIEW_PARAMETER, None)
        bound.arguments[PREVIEW_OPTIONS_PARAMETER] = types.LinkPreviewOptions(
            is_disabled=LINK_PREVIEWS_DISABLED
        )
    elif LEGACY_PREVIEW_PARAMETER in parameters:
        bound.arguments[LEGACY_PREVIEW_PARAMETER] = LINK_PREVIEWS_DISABLED
