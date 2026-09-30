import logging

from telebot import types

from app.constants.runtime import PROJECT_ROOT
from locales.localizer import Localizer
from tg_bot import CBT, utils
from tg_bot.static_keyboards import CLEAR_STATE_BTN
from Utils.plugin_install import PluginInstaller, PluginInstallError
from Utils.plugin_install.constants import MAX_UPLOAD_BYTES
from Utils.plugin_install.service import validate_filename


def upload_keyboard(offset):
    translate = Localizer().translate
    return types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton(
            translate("plugin_upload_back"),
            callback_data=f"{CBT.PLUGINS_LIST}:{offset}",
        )
    )


def download_document(bot, document):
    if document is None:
        raise PluginInstallError("plugin_upload_format")
    filename = validate_filename(document.file_name)
    if not document.file_size or document.file_size > MAX_UPLOAD_BYTES:
        raise PluginInstallError("plugin_upload_size")
    file = bot.get_file(document.file_id)
    return bot.download_file(file.file_path), filename


def error_text(error):
    translate = Localizer().translate
    text = translate(error.key)
    if error.names:
        text += "\n\n" + "\n".join(
            f"<code>{utils.escape(name)}</code>" for name in error.names
        )
    return text


def upload_plugin(controller, message):
    if not controller.menu_user_allowed(message.from_user, message.chat):
        return
    state = controller.get_state(message.chat.id, message.from_user.id)
    if state is None or state["state"] != CBT.UPLOAD_PLUGIN:
        return
    offset = state["data"]["offset"]
    translate = Localizer().translate
    try:
        data, filename = download_document(controller.bot, message.document)
        entry, installed = PluginInstaller(PROJECT_ROOT).install(data, filename)
    except PluginInstallError as error:
        controller.bot.send_message(
            message.chat.id, error_text(error), reply_markup=CLEAR_STATE_BTN()
        )
        return
    except Exception:
        logging.getLogger("TGBot").exception(
            "Plugin upload failed for authorized user %s", message.from_user.id
        )
        controller.bot.send_message(
            message.chat.id,
            translate("plugin_upload_failed"),
            reply_markup=CLEAR_STATE_BTN(),
        )
        return
    finish_upload(controller, message, offset, entry, installed)


def finish_upload(controller, message, offset, entry, installed):
    controller.clear_state(message.chat.id, message.from_user.id, True)
    logging.getLogger("TGBot").info(
        "Plugin package installed by user %s: %s", message.from_user.id, entry
    )
    text = Localizer().translate(
        "plugin_upload_done", utils.escape(entry), len(installed)
    )
    controller.bot.send_message(
        message.chat.id, text, reply_markup=upload_keyboard(offset)
    )
