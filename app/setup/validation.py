import re

from app.constants.setup import (
    BOT_TOKEN_PATTERN,
    BOT_USERNAME_PATTERN,
    BOT_USERNAME_MAX_LENGTH,
    GOLDEN_KEY_LENGTH,
    PASSWORD_MIN_LENGTH,
    PASSWORD_MAX_BYTES,
    USER_AGENT_MAX_LENGTH,
)


def valid_golden_key(value):
    return len(value) == GOLDEN_KEY_LENGTH and value.isascii() and value.isalnum()


def valid_bot_token(value):
    return re.fullmatch(BOT_TOKEN_PATTERN, value, flags=re.ASCII) is not None


def valid_bot_username(value):
    return (
        isinstance(value, str)
        and len(value) <= BOT_USERNAME_MAX_LENGTH
        and re.fullmatch(BOT_USERNAME_PATTERN, value, flags=re.ASCII | re.IGNORECASE)
        is not None
    )


def valid_password(value):
    return (
        len(value) >= PASSWORD_MIN_LENGTH
        and len(value.encode()) <= PASSWORD_MAX_BYTES
        and any(character.isupper() for character in value)
        and any(character.islower() for character in value)
        and any(character.isdigit() for character in value)
    )


def valid_user_agent(value):
    return (
        len(value) <= USER_AGENT_MAX_LENGTH
        and value.isascii()
        and all(character.isprintable() for character in value)
    )
