import hashlib
import re
import stat
import unicodedata
import zipfile
from pathlib import PurePosixPath

from app.constants import update_installation as settings


def release_path(value, directory=False):
    if (
        not isinstance(value, str)
        or not value
        or unicodedata.normalize("NFC", value) != value
    ):
        raise ValueError("Invalid update path")
    name = value.removesuffix("/") if directory else value
    path = PurePosixPath(name)
    if (
        not path.parts
        or path.is_absolute()
        or path.as_posix() != name
        or len(path.parts) > settings.MAX_PATH_DEPTH
    ):
        raise ValueError("Update path is not canonical")
    if any(
        character in settings.FORBIDDEN_PATH_CHARACTERS
        or ord(character) < settings.MIN_PRINTABLE_CHARACTER
        for character in name
    ):
        raise ValueError("Unsafe update path")
    validate_components(path)
    if path.parts[0] not in settings.CODE_ROOTS and name not in settings.ENTRY_FILES:
        raise ValueError("Update contains a protected path")
    if len(path.parts) == 1 and path.parts[0] in settings.CODE_ROOTS and not directory:
        raise ValueError("Update cannot replace a code directory")
    return path


def validate_components(path):
    for part in path.parts:
        if part in {".", ".."} or part.casefold() in settings.FORBIDDEN_COMPONENTS:
            raise ValueError("Update contains a protected component")
        if (
            part.endswith((" ", "."))
            or len(part.encode("utf-8")) > settings.MAX_COMPONENT_BYTES
        ):
            raise ValueError("Update path is not portable")
        if part.split(".")[0].upper() in settings.WINDOWS_RESERVED_NAMES:
            raise ValueError("Update contains a reserved filename")
        if (
            part.startswith(".")
            and part not in settings.ENTRY_FILES
            and part != ".github"
        ):
            raise ValueError("Update contains a hidden path")
    if path.suffix.casefold() in settings.FORBIDDEN_SUFFIXES:
        raise ValueError("Update contains a private file type")


def validate_files(files):
    if not isinstance(files, dict) or not files or len(files) > settings.MAX_FILE_COUNT:
        raise ValueError("Invalid update file manifest")
    paths = []
    for name, digest in files.items():
        paths.append(release_path(name))
        if (
            not isinstance(digest, str)
            or re.fullmatch(settings.SHA256_PATTERN, digest) is None
        ):
            raise ValueError("Invalid update file digest")
    validate_path_collisions(paths)
    return dict(files)


def validate_path_collisions(paths):
    validate_component_casing(paths)
    files = {path.as_posix() for path in paths}
    if len(files) != len(paths):
        raise ValueError("Update contains duplicate files")
    if any(parent.as_posix() in files for path in paths for parent in path.parents):
        raise ValueError("Update contains conflicting file paths")


def validate_component_casing(paths):
    names = {}
    for path in paths:
        for component in (path, *path.parents):
            name = component.as_posix()
            previous = names.setdefault(name.casefold(), name)
            if previous != name:
                raise ValueError("Update contains case-colliding paths")


def archive_members(archive, files):
    members = archive.infolist()
    if (
        len(members) > settings.MAX_FILE_COUNT
        or sum(member.file_size for member in members) > settings.MAX_EXTRACTED_BYTES
    ):
        raise ValueError("Update archive exceeds the limit")
    paths = [release_path(member.orig_filename, member.is_dir()) for member in members]
    folded = [path.as_posix().casefold() for path in paths]
    if len(folded) != len(set(folded)):
        raise ValueError("Update archive contains duplicate paths")
    actual = {
        path.as_posix() for member, path in zip(members, paths) if not member.is_dir()
    }
    if actual != set(files):
        raise ValueError("Update archive differs from the signed manifest")
    validate_component_casing(paths)
    validate_path_collisions(
        [path for member, path in zip(members, paths) if not member.is_dir()]
    )
    for member, path in zip(members, paths):
        validate_member_type(member)
        if member.is_dir() and not any(
            PurePosixPath(name).is_relative_to(path) for name in files
        ):
            raise ValueError("Update archive contains an unexpected directory")
    return [
        (member, path) for member, path in zip(members, paths) if not member.is_dir()
    ]


def validate_member_type(member):
    mode = member.external_attr >> 16
    if member.flag_bits & settings.ZIP_ENCRYPTION_FLAG or stat.S_IFMT(mode) not in {
        0,
        stat.S_IFREG,
        stat.S_IFDIR,
    }:
        raise ValueError("Update archive contains unsupported files")
    if (
        member.file_size > settings.MAX_FILE_BYTES
        or member.file_size
        > max(member.compress_size, 1) * settings.MAX_COMPRESSION_RATIO
    ):
        raise ValueError("Update member exceeds the limit")
    if member.is_dir() and (member.file_size or stat.S_ISREG(mode)):
        raise ValueError("Invalid update directory")
    if stat.S_ISDIR(mode) and not member.is_dir():
        raise ValueError("Invalid update file type")


def extract_member(archive, member, destination, digest):
    destination.parent.mkdir(
        mode=settings.PRIVATE_DIRECTORY_MODE, parents=True, exist_ok=True
    )
    total = 0
    checksum = hashlib.sha256()
    with archive.open(member) as source, destination.open("xb") as target:
        destination.chmod(settings.PRIVATE_FILE_MODE)
        while chunk := source.read(settings.READ_CHUNK_BYTES):
            total += len(chunk)
            if total > member.file_size or total > settings.MAX_FILE_BYTES:
                raise ValueError("Extracted update exceeds the limit")
            checksum.update(chunk)
            target.write(chunk)
        target.flush()
    if total != member.file_size or checksum.hexdigest() != digest:
        raise ValueError("Update file checksum mismatch")
    if destination.suffix.casefold() == ".py":
        compile(destination.read_bytes(), str(destination), "exec", dont_inherit=True)


def extract_release(archive_path, stage, files):
    if (
        archive_path.is_symlink()
        or archive_path.stat().st_size > settings.MAX_ARCHIVE_BYTES
    ):
        raise ValueError("Update archive exceeds the limit")
    with zipfile.ZipFile(archive_path) as archive:
        for member, path in archive_members(archive, files):
            extract_member(
                archive, member, stage.joinpath(*path.parts), files[path.as_posix()]
            )
