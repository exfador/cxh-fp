from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path

from Utils.backups.archive import (
    checked_destination,
    validate_archive,
    validate_member,
    is_excluded_path,
)
from Utils.backups.constants import (
    BACKUP_PATH,
    BACKUP_ROOTS,
    EXCLUDED_DIRECTORIES,
    STAGING_PATH,
    UPLOAD_PATH,
    PRIVATE_FILE_MODE,
    EXCLUDED_PATHS,
    BACKUP_PREVIOUS_PATH,
    MAX_ARCHIVE_FILES,
    MAX_ARCHIVE_BYTES,
)


from Utils.backups.locking import backup_lock
from Utils.backups.restoration import atomic_copy, restore_files


class BackupService:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _source_files(self):
        for name in sorted(BACKUP_ROOTS):
            directory = checked_destination(self.root, Path(name))
            if not directory.exists():
                continue
            for current, directories, files in os.walk(directory, followlinks=False):
                directories[:] = [
                    name
                    for name in sorted(set(directories) - EXCLUDED_DIRECTORIES)
                    if (Path(current) / name).relative_to(self.root)
                    not in EXCLUDED_PATHS
                ]
                for entry in directories + sorted(files):
                    path = Path(current) / entry
                    checked_destination(self.root, path.relative_to(self.root))
                for filename in sorted(files):
                    path = Path(current) / filename
                    if not is_excluded_path(path.relative_to(self.root)):
                        yield path

    def create(self) -> None:
        with backup_lock(self.root):
            self._create()

    def _create(self) -> None:
        with tempfile.NamedTemporaryFile(dir=self.root, delete=False) as file:
            temporary = Path(file.name)
        try:
            self._write_archive(temporary)
            self.check(temporary)
            destination = checked_destination(self.root, BACKUP_PATH)
            if destination.exists():
                atomic_copy(
                    destination, checked_destination(self.root, BACKUP_PREVIOUS_PATH)
                )
            os.chmod(temporary, PRIVATE_FILE_MODE)
            os.replace(temporary, checked_destination(self.root, BACKUP_PATH))
        finally:
            temporary.unlink(missing_ok=True)

    def _write_archive(self, destination: Path) -> None:
        with zipfile.ZipFile(
            destination, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            total = 0
            for count, path in enumerate(self._source_files(), start=1):
                total += path.stat().st_size
                if count > MAX_ARCHIVE_FILES or total > MAX_ARCHIVE_BYTES:
                    raise ValueError("Backup exceeds configured limits")
                archive.write(path, path.relative_to(self.root))
            validate_archive(archive)

    def extract(self) -> None:
        with backup_lock(self.root):
            self._extract()

    def _extract(self) -> None:
        source = checked_destination(self.root, UPLOAD_PATH)
        staging = checked_destination(self.root, STAGING_PATH)
        staging.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=staging.parent) as temporary:
            self._extract_archive(source, Path(temporary))
            if staging.exists():
                shutil.rmtree(staging)
            shutil.move(temporary, staging)

    def _extract_archive(self, source: Path, staging: Path) -> None:
        with zipfile.ZipFile(source) as archive:
            members = validate_archive(archive)
            for member in members:
                relative = Path(validate_member(member))
                destination = checked_destination(staging, relative)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with (
                    archive.open(member) as incoming,
                    destination.open("wb") as outgoing,
                ):
                    shutil.copyfileobj(incoming, outgoing)
                os.chmod(destination, PRIVATE_FILE_MODE)

    def install(self) -> None:
        with backup_lock(self.root):
            self._install()

    def _install(self) -> None:
        staging = checked_destination(self.root, STAGING_PATH)
        if not staging.is_dir():
            raise FileNotFoundError("Backup staging directory is missing")
        files = self._staged_files(staging)
        restore_files(self.root, files)

    def check(self, source=None):
        path = source or checked_destination(self.root, BACKUP_PATH)
        with zipfile.ZipFile(path) as archive:
            members = validate_archive(archive)
            if archive.testzip() is not None:
                raise ValueError("Backup checksum mismatch")
            return {
                "files": len(members),
                "bytes": sum(member.file_size for member in members),
            }

    def restore(self, source):
        with backup_lock(self.root):
            staging = checked_destination(self.root, STAGING_PATH)
            staging.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=staging.parent) as temporary:
                self._extract_archive(source, Path(temporary))
                restore_files(self.root, self._staged_files(Path(temporary)))

    @contextmanager
    def snapshot(self):
        with tempfile.TemporaryFile(mode="w+b") as snapshot:
            with backup_lock(self.root):
                source = checked_destination(self.root, BACKUP_PATH)
                with source.open("rb") as incoming:
                    shutil.copyfileobj(incoming, snapshot)
            snapshot.seek(0)
            yield snapshot

    def _staged_files(self, staging: Path) -> list[tuple[Path, Path]]:
        files = []
        for source in staging.rglob("*"):
            relative = source.relative_to(staging)
            validate_member(zipfile.ZipInfo(relative.as_posix()))
            if relative.parts[0] not in BACKUP_ROOTS:
                raise ValueError("Backup staging contains an unexpected root")
            checked_destination(staging, relative)
            destination = checked_destination(self.root, relative)
            if source.is_file():
                files.append((source, destination))
        return files
