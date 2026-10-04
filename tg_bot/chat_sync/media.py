import io

from tg_bot.constants.chat_sync import CHAT_SYNC_MAX_FILE_BYTES


class UnsupportedMedia(Exception):
    def __init__(self, key):
        super().__init__(key)
        self.key = key


def media_item(message):
    if message.photo:
        return message.photo[-1]
    if message.sticker:
        sticker = message.sticker
        if not sticker.is_animated and not sticker.is_video:
            return sticker
        preview = getattr(sticker, "thumbnail", None) or getattr(sticker, "thumb", None)
        if preview is None:
            raise UnsupportedMedia("cs_media_sticker")
        return preview
    if message.document:
        if not (message.document.mime_type or "").startswith("image/"):
            raise UnsupportedMedia("cs_media_document")
        return message.document
    raise UnsupportedMedia("cs_media_document")


def to_jpeg(data):
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[3])
        output = io.BytesIO()
        background.save(output, format="JPEG", quality=92)
        return output.getvalue()


def needs_conversion(message, path):
    lowered = (path or "").lower()
    mime = (getattr(message.document, "mime_type", "") or "").lower()
    return bool(message.sticker) or lowered.endswith(".webp") or mime == "image/webp"


def download_media(bot, message):
    item = media_item(message)
    if (item.file_size or 0) > CHAT_SYNC_MAX_FILE_BYTES:
        raise UnsupportedMedia("cs_media_size")
    info = bot.get_file(item.file_id)
    data = bot.download_file(info.file_path)
    if needs_conversion(message, info.file_path):
        try:
            data = to_jpeg(data)
        except Exception as error:
            raise UnsupportedMedia("cs_media_sticker") from error
    return data
