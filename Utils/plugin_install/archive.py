import copy
import io
import unicodedata
import zipfile
from pathlib import PurePosixPath

from Utils.backups.archive import validate_member
from Utils.plugin_install.constants import (
    IGNORED_NAMES,
    MAX_ARCHIVE_FILES,
    MAX_COMPONENT_BYTES,
    MAX_COMPRESSION_RATIO,
    MAX_EXTRACTED_BYTES,
    MAX_PATH_DEPTH,
    PLUGIN_DIRECTORY,
    READ_CHUNK_BYTES,
)
from Utils.plugin_install.errors import PluginInstallError


def checked_path(member):
    original = member.orig_filename
    if unicodedata.normalize("NFC", original) != original:
        raise PluginInstallError("plugin_upload_invalid_archive")
    clone = copy.copy(member)
    clone.orig_filename = f"{PLUGIN_DIRECTORY}/{original}"
    try:
        validate_member(clone)
    except ValueError as error:
        raise PluginInstallError("plugin_upload_invalid_archive") from error
    path = PurePosixPath(original)
    if path.is_absolute() or not path.parts or len(path.parts) > MAX_PATH_DEPTH:
        raise PluginInstallError("plugin_upload_invalid_archive")
    if any(len(part.encode("utf-8")) > MAX_COMPONENT_BYTES for part in path.parts):
        raise PluginInstallError("plugin_upload_invalid_archive")
    return path


def checked_members(archive):
    members = archive.infolist()
    if len(members) > MAX_ARCHIVE_FILES:
        raise PluginInstallError("plugin_upload_archive_limit")
    if sum(member.file_size for member in members) > MAX_EXTRACTED_BYTES:
        raise PluginInstallError("plugin_upload_archive_limit")
    paths = [(member, checked_path(member)) for member in members]
    folded = [path.as_posix().casefold() for _, path in paths]
    if len(set(folded)) != len(folded):
        raise PluginInstallError("plugin_upload_invalid_archive")
    files = {
        path.as_posix().casefold() for member, path in paths if not member.is_dir()
    }
    check_parent_casing(paths)
    for member, path in paths:
        if any(parent.as_posix().casefold() in files for parent in path.parents):
            raise PluginInstallError("plugin_upload_invalid_archive")
        if member.file_size > max(member.compress_size, 1) * MAX_COMPRESSION_RATIO:
            raise PluginInstallError("plugin_upload_archive_limit")
    return [
        (member, path) for member, path in paths if not set(path.parts) & IGNORED_NAMES
    ]


def check_parent_casing(paths):
    names = {}
    for _, path in paths:
        for component in (path, *path.parents):
            name = component.as_posix()
            folded = name.casefold()
            if folded in names and names[folded] != name:
                raise PluginInstallError("plugin_upload_invalid_archive")
            names[folded] = name


def write_member(archive, member, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with archive.open(member) as source, destination.open("xb") as target:
        while chunk := source.read(READ_CHUNK_BYTES):
            written += len(chunk)
            if written > member.file_size or written > MAX_EXTRACTED_BYTES:
                raise PluginInstallError("plugin_upload_archive_limit")
            target.write(chunk)
    if written != member.file_size:
        raise PluginInstallError("plugin_upload_invalid_archive")


def extract_archive(data, stage):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member, path in checked_members(archive):
                destination = stage.joinpath(*path.parts)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    write_member(archive, member, destination)
    except (zipfile.BadZipFile, EOFError, RuntimeError, NotImplementedError) as error:
        raise PluginInstallError("plugin_upload_invalid_archive") from error
