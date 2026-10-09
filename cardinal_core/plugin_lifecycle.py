from __future__ import annotations
from cardinal_core import plugin_compat
from cardinal_core.plugin_context import plugin_owner
from cardinal_core.plugin_loading.loader import PluginLoader
from cardinal_core.plugin_loading.constants import PLACEHOLDER_FLAG, PLUGIN_DIRECTORY
from cardinal_core.plugin_loading.diagnostics import error_summary
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    pass
from uuid import UUID
import configparser
import time
import sys
import os
from Utils import cardinal_tools
from threading import RLock, Thread
import cardinal as _module_state


class PluginLifecycle:
    plugin_activation_lock = RLock()

    def run(self):
        self.run_id += 1
        self.start_time = int(time.time())
        Thread(target=self.runner.loop, daemon=True).start()
        self.run_handlers(self.pre_start_handlers, (self,))
        self.run_handlers(self.post_start_handlers, (self,))
        Thread(target=self.lots_raise_loop, daemon=True).start()
        Thread(target=self.update_session_loop, daemon=True).start()
        self.process_events()

    def start(self):
        self.run_id += 1
        self.run_handlers(self.pre_start_handlers, (self,))
        self.run_handlers(self.post_start_handlers, (self,))
        self.process_events()

    def stop(self):
        self.run_id += 1
        self.run_handlers(self.pre_stop_handlers, (self,))
        self.run_handlers(self.post_stop_handlers, (self,))

    def update_lots_and_categories(self):
        result = self._Cardinal__update_profile(
            infinite_polling=False, attempts=3, update_main_profile=False
        )
        return result

    def switch_msg_get_mode(self):
        self.MAIN_CFG["FunPay"]["oldMsgGetMode"] = str(int(not self.old_mode_enabled))
        self.save_config(self.MAIN_CFG, "configs/_main.cfg")
        if not self.runner:
            return
        if not self.old_mode_enabled:
            self.runner.last_messages_ids = {
                k: v[0] for k, v in self.runner.runner_last_messages.items()
            }
        self.runner.make_msg_requests = False if self.old_mode_enabled else True
        if self.old_mode_enabled:
            self.runner.last_messages_ids = {}
            self.runner.by_bot_ids = {}

    @staticmethod
    def save_config(config: configparser.ConfigParser, file_path: str) -> None:
        from app.config_store import write_config

        write_config(config, file_path)

    @staticmethod
    def is_uuid_valid(uuid: str) -> bool:
        try:
            uuid_obj = UUID(uuid, version=4)
        except ValueError:
            return False
        return str(uuid_obj) == uuid

    @staticmethod
    def is_plugin(file: str) -> bool:
        with open(f"plugins/{file}", "r", encoding="utf-8") as f:
            line = f.readline()
        if line.startswith("#"):
            line = line.replace("\n", "")
            args = line.split()
            if "noplug" in args:
                return False
        return True

    @staticmethod
    def load_plugin(from_file: str) -> tuple:
        plugin_compat.install()
        return PluginLoader(PLUGIN_DIRECTORY, frozenset()).load(from_file)

    def load_plugins(self):
        plugin_compat.install()
        if not os.path.exists("plugins"):
            _module_state.logger.warning(_module_state._("crd_no_plugins_folder"))
            return
        plugins = [file for file in os.listdir("plugins") if file.endswith(".py")]
        if not plugins:
            _module_state.logger.info(_module_state._("crd_no_plugins"))
            return
        sys.path.append("plugins")
        for file in plugins:
            try:
                if not self.is_plugin(file):
                    continue
                plugin, data = PluginLoader(
                    PLUGIN_DIRECTORY, set(self.disabled_plugins)
                ).load(file)
            except BaseException as error:
                self.remember_broken(file, error_summary(error))
                _module_state.logger.error(
                    "%s %s",
                    _module_state._("crd_plugin_load_err", file),
                    error_summary(error),
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                continue
            if not self.is_uuid_valid(data["UUID"]):
                self.remember_broken(file, "UUID должен быть строкой UUID v4")
                _module_state.logger.error(_module_state._("crd_invalid_uuid", file))
                continue
            if data["UUID"] in self.plugins:
                self.remember_broken(
                    file,
                    f"UUID {data['UUID']} уже занят плагином "
                    f"«{self.plugins[data['UUID']].name}»",
                )
                _module_state.logger.error(
                    _module_state._(
                        "crd_uuid_already_registered", data["UUID"], data["NAME"]
                    )
                )
                continue
            plugin_data = _module_state.PluginData(
                data["NAME"],
                data["VERSION"],
                data["DESCRIPTION"],
                data["CREDITS"],
                data["UUID"],
                f"plugins/{file}",
                plugin,
                data["SETTINGS_PAGE"],
                data["BIND_TO_DELETE"],
                False if data["UUID"] in self.disabled_plugins else True,
                True if data["UUID"] in self.pinned_plugins else False,
            )
            self.plugins[data["UUID"]] = plugin_data

    def remember_broken(self, file: str, error: str) -> None:
        record = getattr(self, "record_broken", None)
        if record is not None:
            record(file, error)

    def add_handlers_from_plugin(self, plugin, uuid: str | None = None):
        for name in self.handler_bind_var_names:
            try:
                functions = getattr(plugin, name)
            except AttributeError:
                continue
            for func in functions:
                func.plugin_uuid = uuid
            self.handler_bind_var_names[name].extend(functions)
        _module_state.logger.debug(
            _module_state._("crd_handlers_registered", plugin.__name__)
        )

    def add_handlers(self):
        for i in self.plugins:
            plugin = self.plugins[i].plugin
            try:
                self.add_handlers_from_plugin(plugin, i)
            except Exception as error:
                _module_state.logger.error(
                    _module_state._("crd_plugin_handlers_err", self.plugins[i].name)
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                self.plugins[i].enabled = False
                self.plugins[i].load_error = error_summary(error)

    def run_handlers(self, handlers_list: list[Callable], args) -> None:
        for func in handlers_list:
            try:
                plugin_uuid = getattr(func, "plugin_uuid")
                if plugin_uuid is None:
                    func(*args)
                elif plugin_uuid in self.plugins and self.plugins[plugin_uuid].enabled:
                    with plugin_owner(plugin_uuid):
                        func(*args)
            except Exception as ex:
                text = _module_state._("crd_handler_err")
                try:
                    text += f" {ex.short_str()}"
                except:
                    pass
                _module_state.logger.error(text)
                _module_state.logger.debug("TRACEBACK", exc_info=True)

    def add_telegram_commands(self, uuid: str, commands: list[tuple[str, str, bool]]):
        if uuid not in self.plugins:
            return
        for i in commands:
            self.plugins[uuid].commands[i[0]] = i[1]
            if i[2] and self.telegram:
                self.telegram.add_command_to_menu(i[0], i[1])

    def toggle_plugin(self, uuid):
        if vars(self).get("_process_stopping", False):
            return
        data = self.plugins[uuid]
        if not data.enabled and getattr(data.plugin, PLACEHOLDER_FLAG, False):
            self.activate_plugin(uuid)
            return
        data.enabled = not data.enabled
        self.remember_plugin_state(uuid)

    def remember_plugin_state(self, uuid):
        if self.plugins[uuid].enabled and uuid in self.disabled_plugins:
            self.disabled_plugins.remove(uuid)
        elif not self.plugins[uuid].enabled and uuid not in self.disabled_plugins:
            self.disabled_plugins.append(uuid)
        cardinal_tools.cache_disabled_plugins(self.disabled_plugins)

    def activate_plugin(self, uuid) -> bool:
        data = self.plugins[uuid]
        with self.plugin_activation_lock:
            if vars(self).get("_process_stopping", False):
                return False
            if not getattr(data.plugin, PLACEHOLDER_FLAG, False):
                data.enabled = True
                self.remember_plugin_state(uuid)
                return True
            try:
                plugin, fields = PluginLoader(PLUGIN_DIRECTORY, frozenset()).load(
                    os.path.basename(data.path)
                )
                if fields["UUID"] != uuid:
                    sys.modules.pop(plugin.__name__, None)
                    raise ValueError("Plugin changed its declared UUID")
                self.add_handlers_from_plugin(plugin, uuid)
            except BaseException as error:
                data.load_error = error_summary(error)
                _module_state.logger.error(
                    "%s %s",
                    _module_state._("crd_plugin_load_err", os.path.basename(data.path)),
                    data.load_error,
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                return False
            data.name, data.version = fields["NAME"], fields["VERSION"]
            data.description, data.credits = fields["DESCRIPTION"], fields["CREDITS"]
            data.plugin, data.settings_page = plugin, fields["SETTINGS_PAGE"]
            data.delete_handler, data.load_error = fields["BIND_TO_DELETE"], None
            data.enabled = True
            self.remember_plugin_state(uuid)
        self.start_plugin(plugin)
        return True

    def publish_telegram_commands(self) -> dict:
        try:
            self.telegram.setup_commands()
        except Exception:
            _module_state.logger.warning("Произошла ошибка при установке команд.")
            _module_state.logger.debug("TRACEBACK", exc_info=True)
        return dict(self.telegram.commands)

    def pin_plugin(self, uuid):
        self.plugins[uuid].pinned = not self.plugins[uuid].pinned
        if not self.plugins[uuid].pinned and uuid in self.pinned_plugins:
            self.pinned_plugins.remove(uuid)
        elif self.plugins[uuid].pinned and uuid not in self.pinned_plugins:
            self.pinned_plugins.append(uuid)
        cardinal_tools.cache_pinned_plugins(self.pinned_plugins)
