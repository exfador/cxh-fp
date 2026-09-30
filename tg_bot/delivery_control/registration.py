from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardinal import Cardinal
import tg_bot.auto_delivery_cp as _module_state


def init_auto_delivery_cp(crd: Cardinal, *args):
    _module_state.AutoDeliveryControlPanel(crd)
