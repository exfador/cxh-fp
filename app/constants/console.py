STATUS_TEXT = {
    "ru": {
        "account": "FunPay: {name} / ID {id} / активных заказов: {orders}",
        "balance": "Баланс: {rub} RUB / {usd} USD / {eur} EUR",
        "ready": "Готов к работе / лотов: {lots} / плагинов: {plugins}",
        "files": "Журнал: logs/log.log / архивы: logs/archive / остановка: Ctrl+C",
        "features": "Автоподнятие: {raise_} / автоответы: {response} / автовыдача: {delivery}",
        "on": "вкл",
        "off": "выкл",
    },
    "en": {
        "account": "FunPay: {name} / ID {id} / active orders: {orders}",
        "balance": "Balance: {rub} RUB / {usd} USD / {eur} EUR",
        "ready": "Ready / offers: {lots} / plugins: {plugins}",
        "files": "Log: logs/log.log / archives: logs/archive / stop: Ctrl+C",
        "features": "Auto raise: {raise_} / auto replies: {response} / delivery: {delivery}",
        "on": "on",
        "off": "off",
    },
}
DEFAULT_TAIL_LINES = 40
MAX_TAIL_LINES = 1000
TAIL_MAX_BYTES = 2 * 1024 * 1024
