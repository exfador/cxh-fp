from Utils.text_encoding_normalizer import TextEncodingNormalizer
from app.brand_policy import (
    is_legacy_signature,
    rebrand_message_signatures,
    signature_prefix_length,
)
from app.constants.branding import (
    BRAND_SIGNATURE,
    DEFAULT_MESSAGE_SIGNATURE,
    PREVIOUS_MESSAGE_SIGNATURE,
    SIGNATURE_SEPARATOR,
    LINE_ENDINGS,
)
from app.constants.outgoing_messages import IMAGE_DIRECTIVE


def prepare_outgoing_message(text, signature, watermark):
    text = rebrand_message_signatures(TextEncodingNormalizer.normalize(text))
    if not signature or not watermark or text.strip().startswith(IMAGE_DIRECTIVE):
        return text
    if signature in {
        BRAND_SIGNATURE,
        PREVIOUS_MESSAGE_SIGNATURE,
    } or is_legacy_signature(signature):
        signature = DEFAULT_MESSAGE_SIGNATURE
    visible = text.lstrip(LINE_ENDINGS)
    if visible == signature or signature_prefix_length(visible, signature):
        return text
    return signature + SIGNATURE_SEPARATOR + text
