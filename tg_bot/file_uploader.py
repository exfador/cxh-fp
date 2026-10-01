from __future__ import annotations
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from cardinal import Cardinal
    from tg_bot.bot import TGBot
from Utils import (
    config_loader as cfg_loader,
    exceptions as excs,
    cardinal_tools,
    updater,
)
from telebot.types import InlineKeyboardButton as Button
from tg_bot import utils, keyboards, CBT
from tg_bot.static_keyboards import CLEAR_STATE_BTN
from telebot import types
from tg_bot.control.plugin_upload import upload_plugin as install_plugin_upload
import logging
import os
from tg_bot.upload_storage import store_upload, upload_destination
from tg_bot.constants.file_upload import MAX_UPLOAD_BYTES

logger = logging.getLogger("TGBot")


def check_file(
    tg: TGBot,
    msg: types.Message,
    type_: Literal["py", "cfg", "json", "txt"] | None = None,
) -> bool:
    if not msg.document:
        tg.bot.send_message(msg.chat.id, "❌ Файл не обнаружен.")
        return False
    if not any(
        (
            msg.document.file_name.endswith(".cfg"),
            msg.document.file_name.endswith(".txt"),
            msg.document.file_name.endswith(".py"),
            msg.document.file_name.endswith(".json"),
        )
    ):
        tg.bot.send_message(msg.chat.id, "❌ Файл должен быть текстовым.")
        return False
    if type_ is not None and (not msg.document.file_name.endswith(f".{type_}")):
        tg.bot.send_message(
            msg.chat.id,
            f"❌ Неправильный формат файла: <b><u>.{msg.document.file_name.split('.')[-1]}</u></b> (вместо <b><u>.{type_}</u></b>)",
        )
        return False
    if not msg.document.file_size or msg.document.file_size > MAX_UPLOAD_BYTES:
        tg.bot.send_message(msg.chat.id, "❌ Размер файла не должен превышать 20МБ.")
        return False
    return True


def download_file(
    tg: TGBot,
    msg: types.Message,
    file_name: str = "temp_file.txt",
    custom_path: str = "",
) -> bool:
    tg.bot.send_message(msg.chat.id, "⏬ Загружаю файл...")
    try:
        directory = custom_path or "storage/cache"
        upload_destination(directory, file_name)
        file_info = tg.bot.get_file(msg.document.file_id)
        file = tg.bot.download_file(file_info.file_path)
        store_upload(directory, file_name, file)
    except:
        tg.bot.send_message(msg.chat.id, "❌ Произошла ошибка при загрузке файла.")
        logger.debug("TRACEBACK", exc_info=True)
        return False
    return True


def finish_products_upload(tg, message):
    filename = message.document.file_name
    try:
        products_count = cardinal_tools.count_products(f"storage/products/{filename}")
    except Exception:
        tg.bot.send_message(
            message.chat.id, "❌ Произошла ошибка при подсчете товаров."
        )
        logger.debug("TRACEBACK", exc_info=True)
        return
    file_number = os.listdir("storage/products").index(filename)
    keyboard = types.InlineKeyboardMarkup().add(
        Button(
            "✏️ Редактировать файл",
            callback_data=f"{CBT.EDIT_PRODUCTS_FILE}:{file_number}:0",
        )
    )
    logger.info("Products file uploaded by authorized user %s", message.from_user.id)
    tg.bot.send_message(
        message.chat.id,
        f"✅ Файл с товарами <code>storage/products/{utils.escape(filename)}</code> загружен. Товаров в файле: <code>{products_count}.</code>",
        reply_markup=keyboard,
    )


def init_uploader(cardinal: Cardinal):
    tg = cardinal.telegram
    bot = tg.bot

    def act_upload_products_file(c: types.CallbackQuery):
        result = bot.send_message(
            c.message.chat.id,
            "Отправьте файл товаров. Одна строка — один товар.",
            reply_markup=CLEAR_STATE_BTN(),
        )
        tg.set_state(
            c.message.chat.id, result.id, c.from_user.id, CBT.UPLOAD_PRODUCTS_FILE
        )
        bot.answer_callback_query(c.id)

    def upload_products_file(m: types.Message):
        tg.clear_state(m.chat.id, m.from_user.id, True)
        if not check_file(tg, m, type_="txt"):
            return
        try:
            upload_destination("storage/products", m.document.file_name)
        except ValueError:
            bot.send_message(m.chat.id, "❌ Недопустимое имя файла товаров.")
            return
        with cardinal_tools.get_products_file_lock(
            f"storage/products/{m.document.file_name}"
        ):
            if not download_file(
                tg, m, m.document.file_name, custom_path=f"storage/products"
            ):
                return
        finish_products_upload(tg, m)

    def act_upload_main_config(c: types.CallbackQuery):
        result = bot.send_message(
            c.message.chat.id,
            "Отправьте файл основных настроек.",
            reply_markup=CLEAR_STATE_BTN(),
        )
        tg.set_state(c.message.chat.id, result.id, c.from_user.id, "upload_main_config")
        bot.answer_callback_query(c.id)

    def upload_main_config(m: types.Message):
        tg.clear_state(m.chat.id, m.from_user.id, True)
        if not check_file(tg, m, type_="cfg"):
            return
        if not download_file(tg, m, "temp_main.cfg"):
            return
        bot.send_message(m.chat.id, "🔁 Проверяю валидность файла...")
        try:
            new_config = cfg_loader.load_main_config(
                "storage/cache/temp_main.cfg", persist_migrations=False
            )
        except excs.ConfigParseError as e:
            bot.send_message(
                m.chat.id,
                f"❌ Произошла ошибка при обработке основного конфига: <code>{utils.escape(str(e))}</code>",
            )
            return
        except UnicodeDecodeError:
            bot.send_message(
                m.chat.id,
                "Произошла ошибка при расшифровке <code>UTF-8</code>. Убедитесь, что кодировка файла = <code>UTF-8</code>, а формат конца строк = <code>LF</code>.",
            )
            return
        except:
            bot.send_message(
                m.chat.id, "❌ Произошла ошибка при проверке конфига автовыдачи."
            )
            logger.debug("TRACEBACK", exc_info=True)
            return
        cardinal.save_config(new_config, "configs/_main.cfg")
        logger.info(
            f"Пользователь $MAGENTA@{m.from_user.username} (id: {m.from_user.id})$RESET загрузил в бота основной конфиг."
        )
        bot.send_message(
            m.chat.id,
            "Файл основных настроек загружен. Перезапустите бот, чтобы применить его. До перезапуска не меняйте переключатели: они перезапишут загруженный файл.",
        )

    def act_upload_auto_response_config(c: types.CallbackQuery):
        result = bot.send_message(
            c.message.chat.id,
            "Отправьте файл настроек автоответов.",
            reply_markup=CLEAR_STATE_BTN(),
        )
        tg.set_state(
            c.message.chat.id, result.id, c.from_user.id, "upload_auto_response_config"
        )
        bot.answer_callback_query(c.id)

    def upload_auto_response_config(m: types.Message):
        tg.clear_state(m.chat.id, m.from_user.id, True)
        if not check_file(tg, m, type_="cfg"):
            return
        if not download_file(tg, m, "temp_auto_response.cfg"):
            return
        bot.send_message(m.chat.id, "🔁 Проверяю валидность файла...")
        try:
            new_config = cfg_loader.load_auto_response_config(
                "storage/cache/temp_auto_response.cfg"
            )
            raw_new_config = cfg_loader.load_raw_auto_response_config(
                "storage/cache/temp_auto_response.cfg"
            )
        except excs.ConfigParseError as e:
            bot.send_message(
                m.chat.id,
                f"❌ Произошла ошибка при обработке конфига автоответчика: <code>{utils.escape(str(e))}</code>",
            )
            return
        except UnicodeDecodeError:
            bot.send_message(
                m.chat.id,
                "Произошла ошибка при расшифровке <code>UTF-8</code>. Убедитесь, что кодировка файла = <code>UTF-8</code>, а формат конца строк = <code>LF</code>.",
            )
            return
        except:
            bot.send_message(
                m.chat.id, "❌ Произошла ошибка при проверке конфига автоответчика."
            )
            logger.debug("TRACEBACK", exc_info=True)
            return
        cardinal.RAW_AR_CFG, cardinal.AR_CFG = (raw_new_config, new_config)
        cardinal.save_config(cardinal.RAW_AR_CFG, "configs/auto_response.cfg")
        logger.info(
            f"Пользователь $MAGENTA@{m.from_user.username} (id: {m.from_user.id})$RESET загрузил в бота и установил конфиг автоответчика."
        )
        bot.send_message(m.chat.id, "Настройки автоответов применены.")

    def act_upload_auto_delivery_config(c: types.CallbackQuery):
        result = bot.send_message(
            c.message.chat.id,
            "Отправьте файл настроек выдачи.",
            reply_markup=CLEAR_STATE_BTN(),
        )
        tg.set_state(
            c.message.chat.id, result.id, c.from_user.id, "upload_auto_delivery_config"
        )
        bot.answer_callback_query(c.id)

    def upload_auto_delivery_config(m: types.Message):
        tg.clear_state(m.chat.id, m.from_user.id, True)
        if not check_file(tg, m, type_="cfg"):
            return
        if not download_file(tg, m, "temp_auto_delivery.cfg"):
            return
        bot.send_message(m.chat.id, "🔁 Проверяю валидность файла...")
        try:
            new_config = cfg_loader.load_auto_delivery_config(
                "storage/cache/temp_auto_delivery.cfg"
            )
        except excs.ConfigParseError as e:
            bot.send_message(
                m.chat.id,
                f"❌ Произошла ошибка при обработке конфига автовыдачи: <code>{utils.escape(str(e))}</code>",
            )
            return
        except UnicodeDecodeError:
            bot.send_message(
                m.chat.id,
                "Произошла ошибка при расшифровке <code>UTF-8</code>. Убедитесь, что кодировка файла = <code>UTF-8</code>, а формат конца строк = <code>LF</code>.",
            )
            return
        except:
            bot.send_message(
                m.chat.id, "❌ Произошла ошибка при проверке конфига автовыдачи."
            )
            logger.debug("TRACEBACK", exc_info=True)
            return
        cardinal.AD_CFG = new_config
        cardinal.save_config(cardinal.AD_CFG, "configs/auto_delivery.cfg")
        logger.info(
            f"Пользователь $MAGENTA@{m.from_user.username} (id: {m.from_user.id})$RESET загрузил в бота и установил конфиг автовыдачи."
        )
        bot.send_message(m.chat.id, "Настройки выдачи применены.")

    def upload_plugin(m: types.Message):
        install_plugin_upload(tg, m)

    def send_funpay_image(m: types.Message):
        data = tg.get_state(m.chat.id, m.from_user.id)["data"]
        chat_id, username = (data["node_id"], data["username"])
        tg.clear_state(m.chat.id, m.from_user.id, True)
        if not m.photo:
            tg.bot.send_message(
                m.chat.id,
                "❌ Поддерживаются только форматы <code>.png</code>, <code>.jpg</code>, <code>.gif</code>.",
            )
            return
        photo = m.photo[-1]
        if photo.file_size >= 20971520:
            tg.bot.send_message(m.chat.id, "❌ Размер файла не должен превышать 20МБ.")
            return
        try:
            file_info = tg.bot.get_file(photo.file_id)
            file = tg.bot.download_file(file_info.file_path)
            image_id = cardinal.account.upload_image(file, type_="chat")
            result = cardinal.send_message(
                chat_id, f"$photo={image_id}", username, watermark=False
            )
            if not result:
                raise Exception("Нету сообщений")
            tg.bot.reply_to(
                m,
                f'✅ Сообщение отправлено в переписку <a href="https://funpay.com/chat/?node={chat_id}">{username}</a>.',
                reply_markup=keyboards.reply(chat_id, username, again=True),
            )
        except:
            logger.warning("Произошла ошибка при отправке изображения.")
            logger.debug("TRACEBACK", exc_info=True)
            tg.bot.reply_to(
                m,
                f'❌ Не удалось отправить сообщение в переписку <a href="https://funpay.com/chat/?node={chat_id}">{username}</a>. Подробнее в файле <code>logs/log.log</code>',
                reply_markup=keyboards.reply(chat_id, username, again=True),
            )
            return

    def upload_image(m: types.Message, type_: Literal["chat", "offer"] = "chat"):
        tg.clear_state(m.chat.id, m.from_user.id, True)
        if not m.photo:
            tg.bot.send_message(
                m.chat.id,
                "❌ Поддерживаются только форматы <code>.png</code>, <code>.jpg</code>, <code>.gif</code>.",
            )
            return
        photo = m.photo[-1]
        if photo.file_size >= 20971520:
            tg.bot.send_message(m.chat.id, "❌ Размер файла не должен превышать 20МБ.")
            return
        try:
            file_info = tg.bot.get_file(photo.file_id)
            file = tg.bot.download_file(file_info.file_path)
            image_id = cardinal.account.upload_image(file, type_=type_)
        except:
            tg.bot.reply_to(
                m,
                f"❌ Не удалось отправить выгрузить изображение. Подробнее в файле <code>logs/log.log</code>",
            )
            return
        if type_ == "chat":
            s = f"Используйте этот ID в текстах автовыдачи/автоответа с переменной <code>$photo</code>\n\nНапример: <code>$photo={image_id}</code>"
        elif type_ == "offer":
            s = f"Используйте этот ID для добавления картинок к лотам."
        bot.reply_to(
            m,
            f"✅ Изображение выгружено на сервер FunPay.\n\n<b>ID:</b> <code>{image_id}</code>\n\n{s}",
        )

    def upload_chat_image(m: types.Message):
        upload_image(m, type_="chat")

    def upload_offer_image(m: types.Message):
        upload_image(m, type_="offer")

    def upload_backup(m: types.Message):
        from tg_bot.control.backup_files import restore_upload

        tg.clear_state(m.chat.id, m.from_user.id, True)
        restore_upload(tg, m)

    tg.cbq_handler(
        act_upload_products_file, lambda c: c.data == CBT.UPLOAD_PRODUCTS_FILE
    )
    tg.cbq_handler(
        act_upload_auto_response_config,
        lambda c: c.data == "upload_auto_response_config",
    )
    tg.cbq_handler(
        act_upload_auto_delivery_config,
        lambda c: c.data == "upload_auto_delivery_config",
    )
    tg.cbq_handler(act_upload_main_config, lambda c: c.data == "upload_main_config")
    tg.file_handler(CBT.UPLOAD_PRODUCTS_FILE, upload_products_file)
    tg.file_handler("upload_auto_response_config", upload_auto_response_config)
    tg.file_handler("upload_auto_delivery_config", upload_auto_delivery_config)
    tg.file_handler("upload_main_config", upload_main_config)
    tg.file_handler(CBT.UPLOAD_PLUGIN, upload_plugin)
    tg.file_handler(CBT.SEND_FP_MESSAGE, send_funpay_image)
    tg.file_handler(CBT.UPLOAD_CHAT_IMAGE, upload_chat_image)
    tg.file_handler(CBT.UPLOAD_OFFER_IMAGE, upload_offer_image)
    tg.file_handler(CBT.UPLOAD_BACKUP, upload_backup)


BIND_TO_PRE_INIT = [init_uploader]
