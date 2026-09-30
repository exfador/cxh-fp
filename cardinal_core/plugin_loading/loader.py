import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from Utils.exceptions import FieldNotExistsError
from cardinal_core.plugin_loading.constants import PLUGIN_FIELDS, PLACEHOLDER_FLAG
from cardinal_core.plugin_loading.metadata import read_static_metadata


class PluginLoader:
    def __init__(self, directory: Path, disabled_uuids: set[str] | frozenset[str]):
        self.directory = directory.resolve()
        self.disabled_uuids = frozenset(disabled_uuids)

    def load(self, filename: str) -> tuple[ModuleType, dict]:
        path = self._checked_path(filename)
        metadata = read_static_metadata(path)
        if metadata["UUID"] in self.disabled_uuids:
            return self._disabled_placeholder(path, metadata)
        module = self._import_module(path)
        fields = self._module_fields(module, filename)
        if fields["UUID"] != metadata["UUID"]:
            raise ValueError("Plugin changed its declared UUID during initialization")
        return module, fields

    def _checked_path(self, filename: str) -> Path:
        if Path(filename).name != filename or not filename.endswith(".py"):
            raise ValueError("Invalid plugin filename")
        path = self.directory / filename
        if path.is_symlink() or not path.resolve().is_relative_to(self.directory):
            raise ValueError("Plugin source escapes its directory")
        if not path.is_file():
            raise FileNotFoundError(filename)
        return path

    def _import_module(self, path: Path) -> ModuleType:
        name = f"plugins.{path.stem}"
        existing = sys.modules.get(name)
        if (
            existing is not None
            and Path(getattr(existing, "__file__", "")).resolve() == path
        ):
            return existing
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError("Plugin loader is unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        return module

    @staticmethod
    def _module_fields(module: ModuleType, filename: str) -> dict:
        result = {}
        for field in PLUGIN_FIELDS:
            if not hasattr(module, field):
                raise FieldNotExistsError(field, filename)
            result[field] = getattr(module, field)
        return result

    @staticmethod
    def _disabled_placeholder(path: Path, metadata: dict) -> tuple[ModuleType, dict]:
        module = ModuleType(f"plugins.{path.stem}")
        fields = {
            "NAME": metadata.get("NAME", path.stem),
            "VERSION": metadata.get("VERSION", ""),
            "DESCRIPTION": metadata.get("DESCRIPTION", ""),
            "CREDITS": metadata.get("CREDITS", ""),
            "SETTINGS_PAGE": False,
            "UUID": metadata["UUID"],
            "BIND_TO_DELETE": None,
        }
        for name, value in fields.items():
            setattr(module, name, value)
        setattr(module, PLACEHOLDER_FLAG, True)
        return module, fields
