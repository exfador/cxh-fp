from __future__ import annotations

import os
import sys
from pathlib import Path

from cardinal_core import plugin_compat
from cardinal_core.plugin_data import BrokenPlugin
from cardinal_core.plugin_loading.constants import PLACEHOLDER_FLAG, PLUGIN_DIRECTORY
from cardinal_core.plugin_loading.diagnostics import error_summary
from cardinal_core.plugin_loading.loader import PluginLoader
from cardinal_core.plugin_loading.metadata import read_static_metadata
from Utils import cardinal_tools
import cardinal as _module_state

LIFECYCLE_STAGES = (
    "BIND_TO_PRE_INIT",
    "BIND_TO_POST_INIT",
    "BIND_TO_PRE_START",
    "BIND_TO_POST_START",
)


class PluginHotSwap:
    def broken_registry(self) -> dict[str, BrokenPlugin]:
        return self.__dict__.setdefault("broken_plugins", {})

    def record_broken(self, file: str, error: str) -> BrokenPlugin:
        name, uuid = Path(file).stem, None
        try:
            metadata = read_static_metadata(PLUGIN_DIRECTORY / file)
            name = str(metadata.get("NAME") or name)
            uuid = metadata.get("UUID")
        except Exception:
            pass
        entry = BrokenPlugin(file, f"plugins/{file}", name, error, uuid)
        self.broken_registry()[entry.key] = entry
        return entry

    def forget_broken(self, file: str) -> None:
        registry = self.broken_registry()
        for key, entry in list(registry.items()):
            if entry.file == file:
                registry.pop(key)

    def active_stages(self) -> list[str]:
        stages = [LIFECYCLE_STAGES[0]]
        if self.runner is not None:
            stages.append(LIFECYCLE_STAGES[1])
        if self.run_id:
            stages.extend(LIFECYCLE_STAGES[2:])
        return stages

    def start_plugin(self, plugin) -> None:
        for stage in self.active_stages():
            self.run_handlers(list(getattr(plugin, stage, None) or ()), (self,))
        if self.telegram is not None:
            self.publish_telegram_commands()

    def install_plugin(self, file: str) -> tuple[bool, str | None]:
        plugin_compat.install()
        if "plugins" not in sys.path:
            sys.path.append("plugins")
        try:
            if not self.is_plugin(file):
                return False, "Файл помечен #noplug и не загружается как плагин"
        except OSError as error:
            return False, error_summary(error)
        with self.plugin_activation_lock:
            try:
                plugin, fields = PluginLoader(
                    PLUGIN_DIRECTORY, frozenset(self.disabled_plugins)
                ).load(file)
                uuid = fields["UUID"]
                if not self.is_uuid_valid(uuid):
                    raise ValueError("Plugin UUID must be a canonical UUID v4 string")
                if uuid in self.plugins:
                    sys.modules.pop(plugin.__name__, None)
                    raise ValueError(
                        f"UUID {uuid} уже занят плагином «{self.plugins[uuid].name}»"
                    )
                data = _module_state.PluginData(
                    fields["NAME"],
                    fields["VERSION"],
                    fields["DESCRIPTION"],
                    fields["CREDITS"],
                    uuid,
                    f"plugins/{file}",
                    plugin,
                    fields["SETTINGS_PAGE"],
                    fields["BIND_TO_DELETE"],
                    uuid not in self.disabled_plugins,
                    uuid in self.pinned_plugins,
                )
                self.add_handlers_from_plugin(plugin, uuid)
            except BaseException as error:
                summary = error_summary(error)
                self.record_broken(file, summary)
                _module_state.logger.error(
                    "%s %s", _module_state._("crd_plugin_load_err", file), summary
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                return False, summary
            self.plugins[uuid] = data
            self.forget_broken(file)
        if data.enabled and not getattr(plugin, PLACEHOLDER_FLAG, False):
            self.start_plugin(plugin)
        return True, uuid

    def plugin_modules(self, data) -> tuple[str, ...]:
        name = getattr(data.plugin, "__name__", "")
        return (name,) if name else ()

    def unload_plugin(self, uuid: str):
        data = self.plugins.pop(uuid, None)
        if data is None:
            return None
        data.enabled = False
        for handlers in self.handler_bind_var_names.values():
            handlers[:] = [
                func for func in handlers if getattr(func, "plugin_uuid", None) != uuid
            ]
        modules = self.plugin_modules(data)
        if self.telegram is not None:
            self.telegram.forget_plugin_handlers(uuid, modules)
            self.forget_plugin_commands(data)
        for name in modules:
            sys.modules.pop(name, None)
        for registry, cache in (
            (self.disabled_plugins, cardinal_tools.cache_disabled_plugins),
            (self.pinned_plugins, cardinal_tools.cache_pinned_plugins),
        ):
            if uuid in registry:
                registry.remove(uuid)
                cache(registry)
        return data

    def forget_plugin_commands(self, removed) -> None:
        from tg_bot.constants.commands import PUBLIC_COMMANDS

        kept = {command for data in self.plugins.values() for command in data.commands}
        public = dict(PUBLIC_COMMANDS)
        stale = [
            command
            for command in removed.commands
            if command in self.telegram.commands
            and command not in kept
            and command not in public
        ]
        for command in stale:
            self.telegram.commands.pop(command)
        if stale:
            self.publish_telegram_commands()

    def delete_broken_plugin(self, key: str) -> BrokenPlugin | None:
        entry = self.broken_registry().pop(key, None)
        if entry is not None and os.path.isfile(entry.path):
            os.remove(entry.path)
        return entry

    def retry_broken_plugin(self, key: str) -> tuple[bool, str | None]:
        entry = self.broken_registry().get(key)
        if entry is None:
            return False, None
        return self.install_plugin(entry.file)
