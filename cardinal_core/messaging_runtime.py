from __future__ import annotations
from typing import TYPE_CHECKING
from FunPayAPI import types
from app.outgoing_messages import prepare_outgoing_message

if TYPE_CHECKING:
    pass
from tg_bot import (
    auto_response_cp,
    config_loader_cp,
    auto_delivery_cp,
    templates_cp,
    plugins_cp,
    file_uploader,
    authorized_users_cp,
    proxy_cp,
    default_cp,
)
import time
import FunPayAPI
import handlers
from Utils import cardinal_tools
from threading import Thread
import cardinal as _module_state


class MessagingRuntime:
    def parse_message_entities(self, msg_text: str) -> list[str | int | float]:
        msg_text = "\n".join((i.strip() for i in msg_text.split("\n")))
        while "\n\n" in msg_text:
            msg_text = msg_text.replace("\n\n", "\n[a][/a]\n")
        pos = 0
        entities = []
        while entity := cardinal_tools.ENTITY_RE.search(msg_text, pos=pos):
            if text := msg_text[pos : entity.span()[0]].strip():
                entities.extend(self.split_text(text))
            variable = msg_text[entity.span()[0] : entity.span()[1]]
            if variable.startswith("$photo"):
                entities.append(int(variable.split("=")[1]))
            elif variable.startswith("$sleep"):
                entities.append(float(variable.split("=")[1]))
            pos = entity.span()[1]
        else:
            if text := msg_text[pos:].strip():
                entities.extend(self.split_text(text))
        return entities

    def send_message(
        self,
        chat_id: int | str,
        message_text: str,
        chat_name: str | None = None,
        interlocutor_id: int | None = None,
        attempts: int = 3,
        watermark: bool = True,
    ) -> list[FunPayAPI.types.Message] | None:
        message_text = prepare_outgoing_message(
            message_text, self.MAIN_CFG["Other"].get("watermark", ""), watermark
        )
        entities = self.parse_message_entities(message_text)
        if all((isinstance(i, float) for i in entities)) or not entities:
            return
        result = []
        for entity in entities:
            current_attempts = attempts
            while current_attempts:
                try:
                    if isinstance(entity, str):
                        msg = self.account.send_message(
                            chat_id,
                            entity,
                            chat_name,
                            interlocutor_id,
                            None,
                            not self.old_mode_enabled,
                            self.old_mode_enabled,
                            self.keep_sent_messages_unread and self.old_mode_enabled,
                        )
                        result.append(msg)
                        _module_state.logger.info(
                            _module_state._("crd_msg_sent", chat_id)
                        )
                    elif isinstance(entity, int):
                        msg = self.account.send_image(
                            chat_id,
                            entity,
                            chat_name,
                            interlocutor_id,
                            not self.old_mode_enabled,
                            self.old_mode_enabled,
                            self.keep_sent_messages_unread and self.old_mode_enabled,
                        )
                        result.append(msg)
                        _module_state.logger.info(
                            _module_state._("crd_msg_sent", chat_id)
                        )
                    elif isinstance(entity, float):
                        time.sleep(entity)
                    break
                except Exception as ex:
                    _module_state.logger.warning(
                        _module_state._("crd_msg_send_err", chat_id)
                    )
                    _module_state.logger.debug("TRACEBACK", exc_info=True)
                    _module_state.logger.info(
                        _module_state._("crd_msg_attempts_left", current_attempts)
                    )
                    current_attempts -= 1
                    time.sleep(1)
            else:
                _module_state.logger.error(
                    _module_state._("crd_msg_no_more_attempts_err", chat_id)
                )
                return []
        return result

    def get_exchange_rate(
        self,
        base_currency: types.Currency,
        target_currency: types.Currency,
        min_interval: int = 60,
    ):
        assert (
            base_currency != types.Currency.UNKNOWN
            and target_currency != types.Currency.UNKNOWN
        )
        if base_currency == target_currency:
            return 1
        rate, t = self._Cardinal__exchange_rates.get(
            (base_currency, target_currency), (None, 0)
        )
        if t and time.time() < t + min_interval:
            return rate
        for i in range(2, -1, -1):
            try:
                exchange_rate1, currency1 = self.account.get_exchange_rate(
                    base_currency
                )
                self._Cardinal__exchange_rates[currency1, base_currency] = (
                    exchange_rate1,
                    time.time(),
                )
                self._Cardinal__exchange_rates[base_currency, currency1] = (
                    1 / exchange_rate1,
                    time.time(),
                )
                time.sleep(1)
                exchange_rate2, currency2 = self.account.get_exchange_rate(
                    target_currency
                )
                self._Cardinal__exchange_rates[currency2, target_currency] = (
                    exchange_rate2,
                    time.time(),
                )
                self._Cardinal__exchange_rates[target_currency, currency2] = (
                    1 / exchange_rate2,
                    time.time(),
                )
                assert currency1 == currency2
                result = exchange_rate2 / exchange_rate1
                self._Cardinal__exchange_rates[base_currency, target_currency] = (
                    result,
                    time.time(),
                )
                self._Cardinal__exchange_rates[target_currency, base_currency] = (
                    1 / result,
                    time.time(),
                )
                return result
            except:
                _module_state.logger.warning(
                    f"Не удалось получить курс обмена. Осталось попыток: {i}"
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                time.sleep(1)
        raise Exception(
            "Не удалось получить курс обмена: превышено количество попыток."
        )

    def update_session(self, attempts: int = 3) -> bool:
        while attempts:
            try:
                self.account.get(update_phpsessid=True)
                _module_state.logger.info(_module_state._("crd_session_updated"))
                return True
            except TimeoutError:
                _module_state.logger.warning(_module_state._("crd_session_timeout_err"))
            except (
                FunPayAPI.exceptions.UnauthorizedError,
                FunPayAPI.exceptions.RequestFailedError,
            ) as e:
                _module_state.logger.error(e.short_str)
                _module_state.logger.debug(e)
            except:
                _module_state.logger.error(
                    _module_state._("crd_session_unexpected_err")
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
            attempts -= 1
            _module_state.logger.warning(_module_state._("crd_try_again_in_n_secs", 2))
            time.sleep(2)
        else:
            _module_state.logger.error(
                _module_state._("crd_session_no_more_attempts_err")
            )
            return False

    def process_events(self):
        instance_id = self.run_id
        events_handlers = {
            FunPayAPI.events.EventTypes.INITIAL_CHAT: self.init_message_handlers,
            FunPayAPI.events.EventTypes.CHATS_LIST_CHANGED: self.messages_list_changed_handlers,
            FunPayAPI.events.EventTypes.LAST_CHAT_MESSAGE_CHANGED: self.last_chat_message_changed_handlers,
            FunPayAPI.events.EventTypes.NEW_MESSAGE: self.new_message_handlers,
            FunPayAPI.events.EventTypes.INITIAL_ORDER: self.init_order_handlers,
            FunPayAPI.events.EventTypes.ORDERS_LIST_CHANGED: self.orders_list_changed_handlers,
            FunPayAPI.events.EventTypes.NEW_ORDER: self.new_order_handlers,
            FunPayAPI.events.EventTypes.ORDER_STATUS_CHANGED: self.order_status_changed_handlers,
        }
        for event in self.runner.listen(
            requests_delay=int(self.MAIN_CFG["Other"]["requestsDelay"])
        ):
            if instance_id != self.run_id:
                break
            self.run_handlers(events_handlers[event.type], (self, event))

    def lots_raise_loop(self):
        if not self.profile.get_lots():
            _module_state.logger.info(_module_state._("crd_raise_loop_not_started"))
            return
        _module_state.logger.info(_module_state._("crd_raise_loop_started"))
        while True:
            try:
                if not self.MAIN_CFG["FunPay"].getboolean("autoRaise"):
                    time.sleep(10)
                    continue
                next_time = self.raise_lots()
                delay = next_time - int(time.time())
                if delay <= 0:
                    continue
                time.sleep(delay)
            except:
                _module_state.logger.debug("TRACEBACK", exc_info=True)

    def update_session_loop(self):
        _module_state.logger.info(_module_state._("crd_session_loop_started"))
        sleep_time = 3600
        while True:
            time.sleep(sleep_time)
            result = self.update_session()
            sleep_time = 60 if not result else 3600

    def init(self):
        self.add_handlers_from_plugin(handlers)
        self.load_plugins()
        self.add_handlers()
        if self.MAIN_CFG["Telegram"].getboolean("enabled"):
            self._Cardinal__init_telegram()
            for module in [
                auto_response_cp,
                auto_delivery_cp,
                config_loader_cp,
                templates_cp,
                plugins_cp,
                file_uploader,
                authorized_users_cp,
                proxy_cp,
                default_cp,
            ]:
                self.add_handlers_from_plugin(module)
        self.run_handlers(self.pre_init_handlers, (self,))
        if self.MAIN_CFG["Telegram"].getboolean("enabled"):
            try:
                self.telegram.setup_commands()
            except:
                _module_state.logger.warning("Произошла ошибка при установке команд.")
                _module_state.logger.debug("TRACEBACK", exc_info=True)
            Thread(target=self.telegram.run, daemon=True).start()
        self._Cardinal__init_account()
        self.runner = FunPayAPI.Runner(self.account, self.old_mode_enabled)
        self._Cardinal__update_profile()
        self.run_handlers(self.post_init_handlers, (self,))
        return self
