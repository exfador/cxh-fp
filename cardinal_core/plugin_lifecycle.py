from __future__ import annotations
from cardinal_core.plugin_loading.loader import PluginLoader
from cardinal_core.plugin_loading.constants import PLUGIN_DIRECTORY
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    pass
import Utils.exceptions
from uuid import UUID
import importlib.util
import configparser
import time
import sys
import os
from Utils import cardinal_tools
from threading import Thread
import cardinal as _module_state


class PluginLifecycle:
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
        return PluginLoader(PLUGIN_DIRECTORY, frozenset()).load(from_file)

    def load_plugins(self):
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
            except:
                _module_state.logger.error(_module_state._("crd_plugin_load_err", file))
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                continue
            if not self.is_uuid_valid(data["UUID"]):
                _module_state.logger.error(_module_state._("crd_invalid_uuid", file))
                continue
            if data["UUID"] in self.plugins:
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
            except:
                _module_state.logger.error(
                    _module_state._("crd_plugin_handlers_err", self.plugins[i].name)
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                self.plugins[i].enabled = False

    def run_handlers(self, handlers_list: list[Callable], args) -> None:
        for func in handlers_list:
            try:
                plugin_uuid = getattr(func, "plugin_uuid")
                if plugin_uuid is None or (
                    plugin_uuid in self.plugins and self.plugins[plugin_uuid].enabled
                ):
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
        self.plugins[uuid].enabled = not self.plugins[uuid].enabled
        if self.plugins[uuid].enabled and uuid in self.disabled_plugins:
            self.disabled_plugins.remove(uuid)
        elif not self.plugins[uuid].enabled and uuid not in self.disabled_plugins:
            self.disabled_plugins.append(uuid)
        cardinal_tools.cache_disabled_plugins(self.disabled_plugins)

    def pin_plugin(self, uuid):
        self.plugins[uuid].pinned = not self.plugins[uuid].pinned
        if not self.plugins[uuid].pinned and uuid in self.pinned_plugins:
            self.pinned_plugins.remove(uuid)
        elif self.plugins[uuid].pinned and uuid not in self.pinned_plugins:
            self.pinned_plugins.append(uuid)
        cardinal_tools.cache_pinned_plugins(self.pinned_plugins)
