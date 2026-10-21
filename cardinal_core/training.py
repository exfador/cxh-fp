from types import SimpleNamespace

from Utils.cardinal_tools import format_order_text
from cardinal_core.account_operations import AccountOperations
from cardinal_core.messaging_runtime import MessagingRuntime


def simulate(config, scenario):
    if scenario not in {"success", "empty", "timeout"}:
        raise ValueError("Unknown training scenario")
    order = SimpleNamespace(
        id="DEMO0001",
        buyer_username="DemoBuyer",
        buyer_id=0,
        chat_id=0,
        amount=1,
        price=100,
        currency="RUB",
        description="Учебный товар",
        short_description="Учебный товар",
        subcategory=SimpleNamespace(
            name="Учебный раздел",
            fullname="Учебный раздел",
            category=SimpleNamespace(name="Демо"),
        ),
    )
    stages = ["Учебная оплата: заказ DEMO0001, реального платежа нет."]
    if config.getboolean("disable", fallback=False):
        return stages + ["Штатная выдача отключена в выбранном шаблоне."], []
    if scenario == "empty" and config.get("productsFileName"):
        return (
            stages + ["Имитируем пустой остаток: выдача остановлена до отправки."],
            [],
        )
    message = format_order_text(config.get("response", ""), order).replace(
        "$product", "DEMO-CODE-NOT-VALID"
    )
    if not message.strip():
        return stages + ["Шаблон пуст: отправлять нечего."], []
    formatter = SimpleNamespace(split_text=AccountOperations.split_text)
    entities = MessagingRuntime.parse_message_entities(formatter, message)
    parts = [
        (
            item
            if isinstance(item, str)
            else (
                f"[Изображение #{item}; в учебном режиме не отправляется]"
                if type(item) is int
                else f"[Пауза {item} секунд; не выполняется]"
            )
        )
        for item in entities
    ]
    stages.append(
        "Условный резерв: DEMO-CODE-NOT-VALID. Реальный файл товаров не читается."
    )
    if scenario == "timeout":
        stages.append(
            "Имитируем неизвестный результат отправки: ручная проверка, повторная выдача запрещена."
        )
    else:
        stages.append(f"Имитируем успешную отправку: частей сообщения — {len(parts)}.")
    return stages, parts
