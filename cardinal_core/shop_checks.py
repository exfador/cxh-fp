import time
from pathlib import Path

from cardinal_core.native_stock import stock_path
from Utils.cardinal_tools import get_products_file_lock
from Utils.backups.constants import BACKUP_PATH
from FunPayAPI.common.enums import SubCategoryTypes


def section_for(cardinal, description):
    config = cardinal.AD_CFG
    names = config.sections()
    for rule in (
        lambda name: name == description,
        lambda name: description.startswith(name),
        lambda name: name in description,
    ):
        candidates = [name for name in names if rule(name)]
        if candidates:
            return max(candidates, key=len)
    return None


def inventory(config):
    filename = config.get("productsFileName")
    if not filename:
        return None
    path = stock_path(filename)
    with get_products_file_lock(str(path)):
        with path.open(encoding="utf-8") as stream:
            return sum(1 for line in stream if line.rstrip("\r\n"))


def inspect_shop(cardinal):
    problems = []
    profile = cardinal.profile
    if profile is None:
        return [
            {
                "kind": "profile",
                "title": "Профиль ещё не загружен",
                "action": "refresh_lots",
                "argument": "-",
            }
        ]
    if profile.id != cardinal.account.id:
        raise ValueError("Profile owner mismatch")
    counts = {}
    for lot in profile.get_lots():
        if lot.subcategory.type is not SubCategoryTypes.COMMON:
            continue
        section = section_for(cardinal, str(lot.description or ""))
        if section is None:
            problems.append(
                {
                    "kind": "external",
                    "title": f"#{lot.id}: нет привязки штатной выдачи; возможна выдача плагином",
                    "action": "plugin_health",
                    "argument": "-",
                }
            )
            continue
        config = cardinal.AD_CFG[section]
        if section not in counts:
            try:
                counts[section] = inventory(config)
            except (OSError, ValueError):
                counts[section] = -1
        amount = counts[section]
        if config.getboolean("disable", fallback=False):
            reason = "штатная выдача отключена"
        elif amount == -1:
            reason = "файл товаров недоступен"
        elif amount == 0:
            reason = "закончились товары штатной выдачи"
        elif not config.get("response", "").strip():
            reason = "пустой шаблон штатной выдачи"
        else:
            continue
        problems.append(
            {
                "kind": "delivery",
                "title": f"#{lot.id}: {reason}",
                "action": "automation",
                "argument": "-",
            }
        )
    path = Path(BACKUP_PATH)
    if not path.exists() or time.time() - path.stat().st_mtime > 7 * 86400:
        problems.append(
            {
                "kind": "backup",
                "title": "Резервной копии нет или она старше 7 дней",
                "action": "create_backup",
                "argument": "-",
            }
        )
    if not cardinal.MAIN_CFG["FunPay"].getboolean("autoDelivery"):
        problems.append(
            {
                "kind": "global",
                "title": "Штатная автовыдача выключена глобально",
                "action": "automation",
                "argument": "-",
            }
        )
    return sorted(problems, key=lambda row: row["kind"] == "external")
