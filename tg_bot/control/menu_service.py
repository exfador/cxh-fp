from types import SimpleNamespace


class MenuService:
    def menu_command_message(self, call):
        return SimpleNamespace(
            chat=call.message.chat, id=call.message.id, from_user=call.from_user
        )

    def menu_logs(self, call, token, argument):
        if not self.menu_store.begin_read(token):
            return
        try:
            self.send_logs(self.menu_command_message(call))
        finally:
            self.menu_store.finish_read(token)

    def menu_backup(self, call, token, argument):
        if not self.menu_store.begin_read(token):
            return
        try:
            self.get_backup(self.menu_command_message(call))
        finally:
            self.menu_store.finish_read(token)

    def menu_create_backup(self, call, token, argument):
        if not self.menu_store.begin_read(token):
            return
        try:
            with self.menu_backup_lock:
                self.create_backup(self.menu_command_message(call))
        finally:
            self.menu_store.finish_read(token)

    def menu_shutdown(self, call, token, argument):
        self.ask_power_off(self.menu_command_message(call))
