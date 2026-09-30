from tg_bot.constants import profile as settings


def read_profile_text(root, language, field, fallback):
    filename = settings.PROFILE_TEXT_FILES.get((language, field))
    if filename is None:
        return fallback
    directory = root / settings.PROFILE_DIRECTORY
    path = directory / filename
    if directory.is_symlink() or path.is_symlink():
        raise ValueError("Profile text cannot be a symbolic link")
    try:
        with path.open("rb") as stream:
            data = stream.read(settings.PROFILE_TEXT_LIMIT_BYTES + 1)
    except FileNotFoundError:
        return fallback
    if len(data) > settings.PROFILE_TEXT_LIMIT_BYTES:
        raise ValueError("Profile text exceeds the file size limit")
    text = data.decode("utf-8-sig").replace("\r\n", "\n").strip()
    if not text or len(text) > settings.PROFILE_TEXT_LIMITS[field]:
        raise ValueError("Profile text is empty or exceeds the Telegram limit")
    if any(ord(character) < 32 and character != "\n" for character in text):
        raise ValueError("Profile text contains unsupported control characters")
    return text
