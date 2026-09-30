import ast
import os
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipInfo

from Utils.backups.archive import checked_destination
from Utils.backups.locking import backup_lock
from Utils.plugin_install.archive import checked_path, extract_archive
from Utils.plugin_install.constants import (
    MAX_CONFLICT_NAMES,
    MAX_ENTRY_BYTES,
    MAX_UPLOAD_BYTES,
    PLUGIN_DIRECTORY,
    PRIVATE_DIRECTORY_MODE,
    PRIVATE_FILE_MODE,
    RESERVED_ENTRY_NAMES,
    STAGING_DIRECTORY,
    STAGING_PREFIX,
    SUPPORTED_EXTENSIONS,
)
from Utils.plugin_install.errors import PluginInstallError


def validate_filename(filename):
    if not isinstance(filename, str) or not filename:
        raise PluginInstallError("plugin_upload_format")
    path = checked_path(ZipInfo(filename))
    if (
        len(path.parts) != 1
        or PurePosixPath(filename).suffix.lower() not in SUPPORTED_EXTENSIONS
    ):
        raise PluginInstallError("plugin_upload_format")
    return path.stem + path.suffix.lower()


def package_directory(stage):
    entries = list(stage.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return stage


def checked_entry(directory):
    entries = list(directory.iterdir())
    files = [entry for entry in entries if entry.is_file()]
    if len(files) != 1 or files[0].suffix != ".py":
        raise PluginInstallError("plugin_upload_structure")
    entry = files[0]
    if entry.name.casefold() in RESERVED_ENTRY_NAMES:
        raise PluginInstallError("plugin_upload_structure")
    if entry.stat().st_size > MAX_ENTRY_BYTES:
        raise PluginInstallError("plugin_upload_entry_limit")
    try:
        ast.parse(entry.read_bytes(), filename=entry.name)
    except (SyntaxError, ValueError, UnicodeError, RecursionError) as error:
        raise PluginInstallError("plugin_upload_invalid_python") from error
    return entry.name


def protect_files(directory):
    directory.chmod(PRIVATE_DIRECTORY_MODE)
    for path in directory.rglob("*"):
        mode = PRIVATE_DIRECTORY_MODE if path.is_dir() else PRIVATE_FILE_MODE
        path.chmod(mode)


def check_conflicts(destination, entries):
    existing = {path.name.casefold() for path in destination.iterdir()}
    conflicts = [entry.name for entry in entries if entry.name.casefold() in existing]
    if conflicts:
        raise PluginInstallError(
            "plugin_upload_conflict", conflicts[:MAX_CONFLICT_NAMES]
        )


def install_entries(source, destination):
    entries = sorted(source.iterdir(), key=lambda entry: entry.name)
    check_conflicts(destination, entries)
    applied = []
    try:
        for entry in entries:
            target = destination / entry.name
            os.rename(entry, target)
            applied.append((target, source / entry.name))
    except OSError:
        for target, original in reversed(applied):
            os.rename(target, original)
        raise
    return tuple(entry.name for entry in entries)


class PluginInstaller:
    def __init__(self, root):
        self.root = Path(root)

    def install(self, data, filename):
        filename = validate_filename(filename)
        if not isinstance(data, bytes) or not data or len(data) > MAX_UPLOAD_BYTES:
            raise PluginInstallError("plugin_upload_size")
        with backup_lock(self.root):
            return self.install_locked(data, filename)

    def install_locked(self, data, filename):
        destination = checked_destination(self.root, Path(PLUGIN_DIRECTORY))
        destination.mkdir(exist_ok=True)
        run = checked_destination(self.root, Path(STAGING_DIRECTORY))
        run.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=STAGING_PREFIX, dir=run) as temporary:
            stage = Path(temporary)
            if Path(filename).suffix.lower() == ".zip":
                extract_archive(data, stage)
            else:
                (stage / filename).write_bytes(data)
            package = package_directory(stage)
            entry = checked_entry(package)
            protect_files(package)
            installed = install_entries(package, destination)
            return entry, installed
