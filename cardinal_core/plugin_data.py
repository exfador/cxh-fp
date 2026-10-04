from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    pass
from dataclasses import dataclass
from hashlib import sha256
from types import ModuleType
import cardinal as _module_state


@dataclass
class BrokenPlugin:
    file: str
    path: str
    name: str
    error: str
    uuid: str | None = None

    @property
    def key(self) -> str:
        return sha256(self.file.encode("utf-8")).hexdigest()[:12]


def get_cardinal() -> None | _module_state.Cardinal:
    if hasattr(_module_state.Cardinal, "instance"):
        return getattr(_module_state.Cardinal, "instance")


class PluginData:
    def __init__(
        self,
        name: str,
        version: str,
        desc: str,
        credentials: str,
        uuid: str,
        path: str,
        plugin: ModuleType,
        settings_page: bool,
        delete_handler: Callable | None,
        enabled: bool,
        pinned: bool,
    ):
        self.name = name
        self.version = version
        self.description = desc
        self.credits = credentials
        self.uuid = uuid
        self.path = path
        self.plugin = plugin
        self.settings_page = settings_page
        self.commands = {}
        self.delete_handler = delete_handler
        self.enabled = enabled
        self.pinned = pinned
        self.load_error = None
