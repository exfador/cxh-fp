import hashlib
import ast
import os
import secrets
import signal
import subprocess
import sys
from pathlib import Path
from time import monotonic, sleep

from app.constants import update_runtime as settings
from app.constants.runtime import VERSION
from app.updates.dependencies import verify_runtime_dependencies
from app.updates.installer import (
    install_archive,
    rollback_pending,
    commit_pending,
    mark_boot_pending,
)
from app.updates.manifest import verify_envelope
from app.updates.store import load_state, write_state
from app.updates.install_state import safe_path, file_bytes
from app.updates.manifest import version_tuple


class UpdateSupervisor:
    def __init__(self, root, executable=sys.executable):
        self.root = Path(root)
        self.executable = executable
        self.version = VERSION
        self.child = None
        self.stopping = False
        self.nonce = None

    def forward_signal(self, number, frame):
        self.stopping = True
        if self.child is not None and self.child.poll() is None:
            self.child.send_signal(number)

    def launch(self):
        if self.stopping:
            return False
        self.nonce = secrets.token_hex(settings.UPDATE_TOKEN_BYTES)
        environment = dict(os.environ)
        environment[settings.UPDATE_CHILD_FLAG] = settings.UPDATE_CHILD_VALUE
        environment[settings.UPDATE_HEALTH_NONCE] = self.nonce
        self.child = subprocess.Popen(
            [self.executable, str(self.root / "main.py")],
            cwd=self.root,
            env=environment,
        )
        return self.wait_for_health()

    def wait_for_health(self):
        deadline = monotonic() + settings.UPDATE_BOOT_TIMEOUT
        while not self.stopping and self.child.poll() is None:
            if self.valid_health():
                return True
            if monotonic() >= deadline:
                break
            sleep(settings.UPDATE_TICK_SECONDS)
        return False

    def valid_health(self):
        try:
            health = load_state(self.root / settings.UPDATE_HEALTH_PATH)
        except (OSError, ValueError):
            return False
        return (
            health.get("nonce") == self.nonce and health.get("version") == self.version
        )

    def stop_child(self):
        if self.child is None or self.child.poll() is not None:
            return
        self.child.terminate()
        try:
            self.child.wait(timeout=settings.UPDATE_STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            self.child.kill()
            self.child.wait()

    def validated_request(self):
        request = load_state(self.root / settings.UPDATE_REQUEST_PATH)
        self.validate_operator(request)
        manifest = verify_envelope(
            request["envelope"],
            settings.UPDATE_PUBLIC_KEY,
            settings.UPDATE_REPOSITORY,
            self.version,
        )
        path = self.root / "storage" / "updates" / "download.zip"
        if path.is_symlink() or path.stat().st_size != manifest["archive_size"]:
            raise ValueError("Invalid downloaded archive")
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != manifest["archive_sha256"]:
            raise ValueError("Downloaded archive changed")
        verify_runtime_dependencies(self.root, manifest["files"])
        return request, manifest, path

    def validate_operator(self, request):
        if set(request) != settings.UPDATE_SIGNED_FIELDS:
            raise ValueError("Invalid update request")
        if any(
            type(request[field]) is not int or request[field] <= 0
            for field in ("recipient", "message_id")
        ):
            raise ValueError("Invalid update recipient")
        if request["previous_version"] != self.version:
            raise ValueError("Update request belongs to a previous version")
        users = load_state(self.root / settings.UPDATE_AUTH_PATH)
        if str(request["recipient"]) not in users:
            raise PermissionError("Update operator was revoked")

    def apply_request(self):
        if self.stopping:
            return False
        previous_version = self.version
        try:
            request, manifest, archive = self.validated_request()
            if self.start_candidate(request, manifest, archive):
                return True
            self.stop_child()
        except Exception as error:
            if self.child is not None:
                self.stop_child()
            print(
                f"Update failed ({type(error).__name__}); restoring previous code",
                flush=True,
            )
        rollback_pending(self.root)
        self.version = previous_version
        self.record_rollback()
        return False if self.stopping else self.launch()

    def start_candidate(self, request, manifest, archive):
        install_archive(self.root, archive, manifest["files"])
        mark_boot_pending(self.root)
        self.version = manifest["version"]
        if not self.launch():
            return False
        commit_pending(self.root)
        self.record_result(request, "done")
        return True

    def record_result(self, request, status):
        try:
            result = dict(request, status=status, version=self.version)
            write_state(self.root / settings.UPDATE_REQUEST_PATH, result)
        except Exception as error:
            print(
                f"Update result could not be stored ({type(error).__name__})",
                flush=True,
            )

    def record_rollback(self):
        try:
            request = load_state(self.root / settings.UPDATE_REQUEST_PATH)
            self.validate_operator(request)
        except Exception as error:
            print(
                f"Update result request was rejected ({type(error).__name__})",
                flush=True,
            )
            request = {}
        self.record_result(request, "rollback")

    def run(self):
        from Utils.single_instance_guard import SingleInstanceGuard

        SingleInstanceGuard.acquire(self.root / settings.UPDATE_SUPERVISOR_LOCK)
        signal.signal(signal.SIGTERM, self.forward_signal)
        signal.signal(signal.SIGINT, self.forward_signal)
        if rollback_pending(self.root):
            self.version = restored_source_version(self.root)
        if not self.launch():
            self.stop_child()
            return self.failure_status()
        while not self.stopping:
            result = self.child.wait()
            if self.stopping:
                break
            if result != settings.UPDATE_EXIT_CODE:
                return result
            if not self.apply_request():
                self.stop_child()
                return self.failure_status()
        self.stop_child()
        return 0

    def failure_status(self):
        if self.stopping:
            return 0
        return (self.child.returncode or 1) if self.child is not None else 1


def restored_source_version(root):
    source = safe_path(root, "app/constants/runtime.py")
    tree = ast.parse(file_bytes(source), filename=str(source))
    values = [node.value.value for node in tree.body if is_version_assignment(node)]
    if len(values) != 1:
        raise ValueError("Restored source version is ambiguous")
    version_tuple(values[0])
    return values[0]


def is_version_assignment(node):
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "VERSION"
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def main(root):
    return UpdateSupervisor(root).run()
