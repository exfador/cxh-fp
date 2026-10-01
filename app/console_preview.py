import logging
import sys

from app.constants.branding import PROJECT_NAME
from app.constants.runtime import VERSION
from app.setup.terminal import SetupConsole
from Utils.logging_support.formatters import CLILoggerFormatter


def preview(stream=None):
    stream = sys.stdout if stream is None else stream
    formatter = CLILoggerFormatter(stream=stream)
    console = SetupConsole(
        writer=lambda value: stream.write(value + "\n"), color=formatter.color
    )
    console.banner("Журнал работы / Runtime log")
    console.write("ПРЕДПРОСМОТР ЖУРНАЛА / LOG PREVIEW")
    console.write("Демонстрационные события. Бот и сетевые запросы не запускаются.\n")
    events = (
        ("main", logging.INFO, f"{PROJECT_NAME} v{VERSION} — запуск"),
        (
            "CoxerHubBot.telegram",
            logging.INFO,
            "Telegram подключён. Панель управления готова.",
        ),
        (
            "FunPayAPI",
            logging.INFO,
            "FunPay подключён. Профиль и список лотов обновлены.",
        ),
        ("main", logging.INFO, "Готов к работе. Остановка: Ctrl+C"),
        (
            "FunPayAPI",
            logging.WARNING,
            "Сервер не ответил вовремя. Проверка будет повторена.",
        ),
        (
            "FPC.example",
            logging.ERROR,
            "Не удалось загрузить плагин. Подробности: logs/log.log",
        ),
        ("CoxerHubBot.telegram", logging.INFO, "Настройки уведомлений сохранены."),
    )
    for name, level, text in events:
        record = logging.LogRecord(name, level, "", 0, text, (), None)
        stream.write(formatter.format(record) + "\n")
    return 0
