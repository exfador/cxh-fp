from __future__ import annotations

import stat
import zipfile
from pathlib import Path, PurePosixPath

from Utils.backups.constants import (
    BACKUP_ROOTS,
    MAX_ARCHIVE_BYTES,
    MAX_ARCHIVE_FILES,
    ZIP_ENCRYPTION_FLAG,
    EXCLUDED_PATHS,
    WINDOWS_RESERVED_NAMES,
    WINDOWS_FORBIDDEN_CHARACTERS,
    MIN_PRINTABLE_CHARACTER,
)


def is_excluded_path(path: PurePosixPath) -> bool:
    folded = PurePosixPath(path.as_posix().casefold())
    return any(
        folded.is_relative_to(PurePosixPath(excluded.as_posix().casefold()))
        for excluded in EXCLUDED_PATHS
    )


def validate_portable_path(path: PurePosixPath) -> None:
    if any(part.endswith((" ", ".")) for part in path.parts):
        raise ValueError("Archive path is not portable")
    if any(part.split(".")[0].upper() in WINDOWS_RESERVED_NAMES for part in path.parts):
        raise ValueError("Archive contains a reserved filename")


def validate_member(member: zipfile.ZipInfo) -> PurePosixPath:
    if member.flag_bits & ZIP_ENCRYPTION_FLAG:
        raise ValueError("Encrypted archives are unsupported")
    name = member.orig_filename
    path = PurePosixPath(name)
    forbidden = any(
        char in WINDOWS_FORBIDDEN_CHARACTERS or ord(char) < MIN_PRINTABLE_CHARACTER
        for char in name
    )
    if forbidden or path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe archive path")
    if not path.parts or path.parts[0] not in BACKUP_ROOTS:
        raise ValueError("Archive contains files outside backup roots")
    if is_excluded_path(path):
        raise ValueError("Archive contains backup staging artifacts")
    validate_portable_path(path)
    mode = member.external_attr >> 16
    if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ValueError("Archive contains unsupported file types")
    return path


def validate_archive(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    if len(members) > MAX_ARCHIVE_FILES:
        raise ValueError("Archive has too many members")
    if sum(member.file_size for member in members) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive is too large")
    names = [validate_member(member).as_posix() for member in members]
    folded = [name.casefold() for name in names]
    if len(folded) != len(set(folded)):
        raise ValueError("Archive has duplicate paths")
    files = {
        name.casefold() for name, member in zip(names, members) if not member.is_dir()
    }
    for name in names:
        if any(
            parent.as_posix().casefold() in files
            for parent in PurePosixPath(name).parents
        ):
            raise ValueError("Archive has conflicting file and directory paths")
    return members


def checked_destination(root: Path, relative: Path) -> Path:
    destination = root / relative
    for part in (destination, *destination.parents):
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError("Backup path contains a symbolic link")
    if not destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("Backup path escapes its root")
    return destination
