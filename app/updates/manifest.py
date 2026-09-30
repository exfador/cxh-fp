import base64
import binascii
import json
import re
import unicodedata
from pathlib import PurePosixPath

from app.updates import constants as settings


class ManifestError(ValueError):
    pass


def canonical_manifest(manifest):
    return json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def reject_duplicate_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(settings.MANIFEST_ERROR)
        result[key] = value
    return result


def parse_envelope(data):
    if not isinstance(data, bytes) or len(data) > settings.MAX_MANIFEST_BYTES:
        raise ManifestError(settings.MANIFEST_ERROR)
    try:
        envelope = json.loads(
            data.decode("utf-8"), object_pairs_hook=reject_duplicate_fields
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ManifestError(settings.MANIFEST_ERROR) from error
    check_fields(envelope, settings.ENVELOPE_FIELDS)
    return envelope


def check_fields(value, names):
    if type(value) is not dict or set(value) != names:
        raise ManifestError(settings.MANIFEST_ERROR)


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"(?:0|[1-9]\d{0,5})\.(?:0|[1-9]\d{0,5})(?:\.(?:0|[1-9]\d{0,5}))?",
        value,
        re.ASCII,
    ):
        raise ManifestError(settings.MANIFEST_ERROR)
    parts = tuple(int(part) for part in value.split("."))
    return parts + (0,) * (settings.VERSION_COMPONENTS - len(parts))


def checked_repository(value):
    if not isinstance(value, str) or len(value) > settings.MAX_REPOSITORY_LENGTH:
        raise ManifestError(settings.REPOSITORY_ERROR)
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value
    ):
        raise ManifestError(settings.REPOSITORY_ERROR)
    if value.endswith(".") or value.endswith(".git"):
        raise ManifestError(settings.REPOSITORY_ERROR)
    return value


def checked_digest(value):
    if not isinstance(value, str) or len(value) != settings.DIGEST_HEX_LENGTH:
        raise ManifestError(settings.MANIFEST_ERROR)
    if any(character not in settings.HEX_CHARACTERS for character in value):
        raise ManifestError(settings.MANIFEST_ERROR)
    return value


def checked_file_path(value):
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > settings.MAX_FILE_PATH_BYTES
    ):
        raise ManifestError(settings.MANIFEST_ERROR)
    if value != unicodedata.normalize("NFC", value):
        raise ManifestError(settings.MANIFEST_ERROR)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {".", ".."} for part in value.split("/"))
    ):
        raise ManifestError(settings.MANIFEST_ERROR)
    if any(
        character in settings.PORTABLE_FORBIDDEN_CHARACTERS or ord(character) < 32
        for character in value
    ):
        raise ManifestError(settings.MANIFEST_ERROR)
    if any(
        part.endswith((" ", "."))
        or part.split(".")[0].upper() in settings.WINDOWS_RESERVED_NAMES
        for part in path.parts
    ):
        raise ManifestError(settings.MANIFEST_ERROR)
    if any(part.casefold() in settings.PRIVATE_MANIFEST_ROOTS for part in path.parts):
        raise ManifestError(settings.MANIFEST_ERROR)
    return value


def checked_files(value):
    if type(value) is not dict or not 1 <= len(value) <= settings.MAX_MANIFEST_FILES:
        raise ManifestError(settings.MANIFEST_ERROR)
    result = {
        checked_file_path(path): checked_digest(digest)
        for path, digest in value.items()
    }
    folded = {path.casefold() for path in result}
    if len(folded) != len(result):
        raise ManifestError(settings.MANIFEST_ERROR)
    for path in result:
        if any(
            parent.as_posix().casefold() in folded
            for parent in PurePosixPath(path).parents
        ):
            raise ManifestError(settings.MANIFEST_ERROR)
    return result


def validate_manifest(manifest, repository, current_version):
    check_fields(manifest, settings.MANIFEST_FIELDS)
    if checked_repository(manifest["repository"]) != checked_repository(repository):
        raise ManifestError(settings.REPOSITORY_ERROR)
    if version_tuple(manifest["version"]) <= version_tuple(current_version):
        raise ManifestError(settings.DOWNGRADE_ERROR)
    checked_digest(manifest["archive_sha256"])
    size = manifest["archive_size"]
    if type(size) is not int or not 1 <= size <= settings.MAX_ARCHIVE_BYTES:
        raise ManifestError(settings.MANIFEST_ERROR)
    checked_files(manifest["files"])
    if len(canonical_manifest(manifest)) > settings.MAX_MANIFEST_BYTES:
        raise ManifestError(settings.MANIFEST_ERROR)
    return json.loads(canonical_manifest(manifest))


def decode_public_key(value):
    if isinstance(value, str):
        if len(value) != settings.PUBLIC_KEY_BYTES * 2 or not all(
            character.lower() in settings.HEX_CHARACTERS for character in value
        ):
            raise ManifestError(settings.SIGNATURE_ERROR)
        value = bytes.fromhex(value)
    if type(value) is not bytes or len(value) != settings.PUBLIC_KEY_BYTES:
        raise ManifestError(settings.SIGNATURE_ERROR)
    return value


def decode_signature(value):
    if (
        not isinstance(value, str)
        or len(value) != ((settings.SIGNATURE_BYTES + 2) // 3) * 4
    ):
        raise ManifestError(settings.SIGNATURE_ERROR)
    try:
        signature = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ManifestError(settings.SIGNATURE_ERROR) from error
    if (
        len(signature) != settings.SIGNATURE_BYTES
        or base64.b64encode(signature).decode("ascii") != value
    ):
        raise ManifestError(settings.SIGNATURE_ERROR)
    return signature


def verify_signature(manifest, signature, public_key):
    try:
        from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as error:
        raise ManifestError(settings.CRYPTOGRAPHY_REQUIRED) from error
    try:
        key = Ed25519PublicKey.from_public_bytes(decode_public_key(public_key))
        key.verify(decode_signature(signature), canonical_manifest(manifest))
    except (InvalidSignature, UnsupportedAlgorithm, ValueError) as error:
        raise ManifestError(settings.SIGNATURE_ERROR) from error


def verify_envelope(envelope, public_key, repository, current_version):
    check_fields(envelope, settings.ENVELOPE_FIELDS)
    manifest = validate_manifest(envelope["manifest"], repository, current_version)
    verify_signature(manifest, envelope["signature"], public_key)
    return manifest
