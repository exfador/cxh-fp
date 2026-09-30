import unicodedata

from app.constants.branding import (
    BRAND_SIGNATURE,
    DEFAULT_MESSAGE_SIGNATURE,
    LEGACY_BRAND_ICONS,
    LEGACY_BRAND_SIGNATURES,
    LEGACY_BRAND_STYLIZATIONS,
    LEGACY_PROJECT_WORDS,
    LEGACY_WEAK_SIGNATURES,
    LINE_ENDINGS,
    MESSAGE_CONFIG_FIELDS,
    MESSAGE_SIGNATURE_HEADER,
    PREVIOUS_MESSAGE_SIGNATURE,
    PREVIOUS_MESSAGE_SIGNATURE_LINES,
    SIGNATURE_LINE_SEPARATORS,
)


def normalized_signature(signature):
    normalized = unicodedata.normalize("NFKC", signature).strip().casefold()
    for stylization in LEGACY_BRAND_STYLIZATIONS:
        normalized = normalized.replace(
            stylization.casefold(), LEGACY_PROJECT_WORDS[-1]
        )
    return "".join(character for character in normalized if character.isalnum())


def is_legacy_signature(signature):
    normalized = unicodedata.normalize("NFKC", signature).strip().casefold()
    if normalized in LEGACY_BRAND_SIGNATURES:
        return True
    compact = normalized_signature(signature)
    if compact == normalized_signature(BRAND_SIGNATURE):
        return any(icon in signature for icon in LEGACY_BRAND_ICONS)
    aliases = {normalized_signature(value) for value in LEGACY_BRAND_SIGNATURES}
    aliases.add("".join(LEGACY_PROJECT_WORDS))
    return bool(compact) and compact in aliases


def rebrand_previous_signature(text):
    lines = text.splitlines(keepends=True)
    populated = [index for index, line in enumerate(lines) if line.strip()]
    if not populated:
        return text
    count = len(PREVIOUS_MESSAGE_SIGNATURE_LINES)
    for index in {populated[0], populated[-1] - count + 1}:
        if index < 0:
            continue
        group = tuple(
            line.rstrip(LINE_ENDINGS) for line in lines[index : index + count]
        )
        if group == PREVIOUS_MESSAGE_SIGNATURE_LINES:
            header = lines[index].rstrip(LINE_ENDINGS)
            lines[index] = MESSAGE_SIGNATURE_HEADER + lines[index][len(header) :]
    return "".join(lines)


def rebrand_message_signatures(text):
    text = rebrand_previous_signature(text)
    lines = text.splitlines(keepends=True)
    populated = [index for index, line in enumerate(lines) if line.strip()]
    if not populated:
        return text
    for index in {populated[0], populated[-1]}:
        signature = lines[index].rstrip(LINE_ENDINGS)
        if is_message_signature(signature):
            ending = lines[index][len(signature) :]
            lines[index] = DEFAULT_MESSAGE_SIGNATURE + ending
    return "".join(lines)


def is_message_signature(signature):
    if signature.strip() == BRAND_SIGNATURE:
        return True
    if not is_legacy_signature(signature):
        return False
    if normalized_signature(signature) not in LEGACY_WEAK_SIGNATURES:
        return True
    decorated = any(icon in signature for icon in LEGACY_BRAND_ICONS)
    stylized = any(
        value.casefold() in signature.casefold() for value in LEGACY_BRAND_STYLIZATIONS
    )
    return (
        decorated or stylized or unicodedata.normalize("NFKC", signature) != signature
    )


def signature_prefix_length(text, signature):
    if not signature:
        return 0
    return next(
        (
            len(signature) + len(ending)
            for ending in SIGNATURE_LINE_SEPARATORS
            if text.startswith(signature + ending)
        ),
        0,
    )


def message_signature_body(text, signature, hide):
    text = rebrand_message_signatures(text)
    visible = text.lstrip(LINE_ENDINGS)
    leading = text[: len(text) - len(visible)]
    length = next(
        (
            length
            for value in (signature, DEFAULT_MESSAGE_SIGNATURE, BRAND_SIGNATURE)
            if (length := signature_prefix_length(visible, value))
        ),
        0,
    )
    return (leading + visible[length:], True) if hide and length else (text, False)


def migrate_message_templates(config):
    changed = False
    for section in config.sections():
        for field, value in config.items(section):
            if field.casefold() not in MESSAGE_CONFIG_FIELDS:
                continue
            replacement = rebrand_message_signatures(value)
            if replacement != value:
                config.set(section, field, replacement)
                changed = True
    return changed


def migrate_brand_signature(config):
    signature = config.get("Other", "watermark", fallback="")
    known_default = signature in {BRAND_SIGNATURE, PREVIOUS_MESSAGE_SIGNATURE}
    if not known_default and not is_legacy_signature(signature):
        return False
    config.set("Other", "watermark", DEFAULT_MESSAGE_SIGNATURE)
    return True
