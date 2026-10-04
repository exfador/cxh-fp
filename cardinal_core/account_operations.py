from __future__ import annotations
from app.constants.branding import PROJECT_NAME
from typing import TYPE_CHECKING
from FunPayAPI import types
from FunPayAPI.common.enums import SubCategoryTypes

if TYPE_CHECKING:
    pass
import datetime
import random
import time
import requests
import FunPayAPI
from FunPayAPI import utils as fp_utils
from Utils import cardinal_tools
from cardinal_core.raise_schedule import save_raise_schedule
import tg_bot.bot
import cardinal as _module_state


class AccountOperations:
    def _Cardinal__init_account(self) -> None:
        while True:
            try:
                self.account.get()
                self.balance = self.get_balance()
                greeting_text = cardinal_tools.create_greeting_text(self)
                cardinal_tools.set_console_title(
                    f"{PROJECT_NAME} - {self.account.username} ({self.account.id})"
                )
                for line in greeting_text.split("\n"):
                    _module_state.logger.info(line)
                break
            except TimeoutError:
                _module_state.logger.error(_module_state._("crd_acc_get_timeout_err"))
            except (
                FunPayAPI.exceptions.UnauthorizedError,
                FunPayAPI.exceptions.RequestFailedError,
            ) as e:
                _module_state.logger.error(e.short_str())
                _module_state.logger.debug(f"TRACEBACK {e.short_str()}")
            except requests.RequestException as error:
                _module_state.logger.error(
                    "Не удалось подключиться к FunPay: %s. Проверьте доступность funpay.com; подробности в logs/log.log.",
                    type(error).__name__,
                )
                _module_state.logger.debug("FunPay connection traceback", exc_info=True)
            except:
                _module_state.logger.error(
                    _module_state._("crd_acc_get_unexpected_err")
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
            _module_state.logger.warning(_module_state._("crd_try_again_in_n_secs", 2))
            time.sleep(2)

    def _Cardinal__update_profile(
        self,
        infinite_polling: bool = True,
        attempts: int = 0,
        update_telegram_profile: bool = True,
        update_main_profile: bool = True,
    ) -> bool:
        _module_state.logger.info(_module_state._("crd_getting_profile_data"))
        while attempts or infinite_polling:
            try:
                profile = self.account.get_user(self.account.id)
                break
            except TimeoutError:
                _module_state.logger.error(
                    _module_state._("crd_profile_get_timeout_err")
                )
            except FunPayAPI.exceptions.RequestFailedError as e:
                _module_state.logger.error(e.short_str())
                _module_state.logger.debug(e)
            except:
                _module_state.logger.error(
                    _module_state._("crd_profile_get_unexpected_err")
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
            attempts -= 1
            _module_state.logger.warning(_module_state._("crd_try_again_in_n_secs", 2))
            time.sleep(2)
        else:
            _module_state.logger.error(
                _module_state._("crd_profile_get_too_many_attempts_err", attempts)
            )
            return False
        if update_main_profile:
            self.profile = profile
            self.curr_profile = profile
            self.lots_ids = [i.id for i in profile.get_lots()]
            _module_state.logger.info(
                _module_state._(
                    "crd_profile_updated",
                    len(profile.get_lots()),
                    len(profile.get_sorted_lots(2)),
                )
            )
        if update_telegram_profile:
            self.tg_profile = profile
            self.last_telegram_lots_update = datetime.datetime.now()
            _module_state.logger.info(
                _module_state._(
                    "crd_tg_profile_updated",
                    len(profile.get_lots()),
                    len(profile.get_sorted_lots(2)),
                )
            )
        return True

    def _Cardinal__init_telegram(self) -> None:
        self.telegram = tg_bot.bot.TGBot(self)
        self.telegram.init()

    def get_balance(self, attempts: int = 3) -> FunPayAPI.types.Balance:
        subcategories = self.account.get_sorted_subcategories().get(
            FunPayAPI.enums.SubCategoryTypes.COMMON, {}
        )
        lots = []
        while not lots and attempts > 0 and subcategories:
            attempts -= 1
            subcat_id = random.choice(list(subcategories.keys()))
            lots = self.account.get_subcategory_public_lots(
                FunPayAPI.enums.SubCategoryTypes.COMMON, subcat_id
            )
        if not lots:
            raise ValueError("No public lots available to retrieve the balance")
        balance = self.account.get_balance(random.choice(lots).id)
        return balance

    def raise_lots(self) -> float:
        next_call = float("inf")
        for subcat in sorted(
            list(self.curr_profile.get_sorted_lots(2).keys()),
            key=lambda x: x.category.position,
        ):
            if subcat.type is SubCategoryTypes.CURRENCY:
                continue
            if (
                saved_time := self.raise_time.get(subcat.category.id)
            ) and saved_time > int(time.time()):
                next_call = saved_time if saved_time < next_call else next_call
                continue
            raise_ok = False
            error_text = ""
            time_delta = ""
            try:
                wait_time = self.account.raise_lots(subcat.category.id)
                _module_state.logger.info(
                    _module_state._("crd_lots_raised", subcat.category.name)
                )
                raise_ok = True
                last_time = self.raised_time.get(subcat.category.id)
                self.raised_time[subcat.category.id] = new_time = int(time.time())
                time_delta = (
                    ""
                    if not last_time
                    else f" Последнее поднятие: {cardinal_tools.time_to_str(new_time - last_time)} назад."
                )
                error_text = f"Подождите {cardinal_tools.time_to_str(wait_time)}."
            except FunPayAPI.exceptions.RaiseError as e:
                if e.error_message is not None:
                    error_text = e.error_message
                if e.wait_time is not None:
                    _module_state.logger.warning(
                        _module_state._(
                            "crd_raise_time_err",
                            subcat.category.name,
                            error_text,
                            cardinal_tools.time_to_str(e.wait_time),
                        )
                    )
                    wait_time = e.wait_time
                else:
                    _module_state.logger.error(
                        _module_state._(
                            "crd_raise_unexpected_err", subcat.category.name
                        )
                    )
                    time.sleep(10)
                    wait_time = 1
            except Exception as e:
                t = 10
                if isinstance(
                    e, FunPayAPI.exceptions.RequestFailedError
                ) and e.status_code in (503, 403, 429):
                    _module_state.logger.warning(
                        _module_state._(
                            "crd_raise_status_code_err",
                            e.status_code,
                            subcat.category.name,
                        )
                    )
                    t = 60
                else:
                    _module_state.logger.error(
                        _module_state._(
                            "crd_raise_unexpected_err", subcat.category.name
                        )
                    )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                time.sleep(t)
                wait_time = 1
            next_time = time.time() + wait_time + 1
            time.sleep(2)
            self.raise_time[subcat.category.id] = next_time
            save_raise_schedule(self.raise_time, self.raised_time)
            next_call = next_time if next_time < next_call else next_call
            if raise_ok:
                self.run_handlers(
                    self.post_lots_raise_handlers,
                    (self, subcat.category, error_text + time_delta),
                )
        return next_call if next_call < float("inf") else time.time() + 10

    def get_order_from_object(
        self,
        obj: types.OrderShortcut | types.Message | types.ChatShortcut,
        order_id: str | None = None,
    ) -> None | types.Order:
        if obj._order_attempt_error:
            return
        if obj._order_attempt_made:
            while obj._order is None and (not obj._order_attempt_error):
                time.sleep(0.1)
            return obj._order
        obj._order_attempt_made = True
        if type(obj) not in (types.Message, types.ChatShortcut, types.OrderShortcut):
            obj._order_attempt_error = True
            raise Exception("Неправильный тип объекта")
        if not order_id:
            if isinstance(obj, types.OrderShortcut):
                order_id = obj.id
                if order_id == "ADTEST":
                    obj._order_attempt_error = True
                    return
            elif isinstance(obj, types.Message) or isinstance(obj, types.ChatShortcut):
                order_id = fp_utils.RegularExpressions().ORDER_ID.findall(str(obj))
                if not order_id:
                    obj._order_attempt_error = True
                    return
                order_id = order_id[0][1:]
        for i in range(2, -1, -1):
            try:
                obj._order = self.account.get_order(order_id)
                _module_state.logger.info(f"Получил информацию о заказе {obj._order}")
                return obj._order
            except:
                _module_state.logger.warning(
                    f"Произошла ошибка при получении заказа #{order_id}. Осталось {i} попыток."
                )
                _module_state.logger.debug("TRACEBACK", exc_info=True)
                time.sleep(1)
        obj._order_attempt_error = True

    @staticmethod
    def split_text(text: str) -> list[str]:
        output = []
        lines = text.split("\n")
        while lines:
            subtext = "\n".join(lines[:20])
            del lines[:20]
            if (strip := subtext.strip()) and strip != "[a][/a]":
                output.append(subtext)
        return output
