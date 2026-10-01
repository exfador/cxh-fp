import logging
import sys

from app.constants.console import STATUS_TEXT


def runtime_banner():
    from app.setup.terminal import SetupConsole
    from app.terminal_colors import supports_color

    SetupConsole(
        writer=lambda line: print(line, file=sys.stderr),
        color=supports_color(sys.stderr),
    ).banner("Журнал работы / Runtime log")


def account_summary(cardinal):
    text = STATUS_TEXT.get(cardinal.MAIN_CFG["Other"]["language"], STATUS_TEXT["ru"])
    return "\n".join(
        (
            text["account"].format(
                name=cardinal.account.username,
                id=cardinal.account.id,
                orders=cardinal.account.active_sales,
            ),
            text["balance"].format(
                rub=cardinal.balance.total_rub,
                usd=cardinal.balance.total_usd,
                eur=cardinal.balance.total_eur,
            ),
        )
    )


def log_ready(cardinal):
    text = STATUS_TEXT.get(cardinal.MAIN_CFG["Other"]["language"], STATUS_TEXT["ru"])
    flags = cardinal.MAIN_CFG["FunPay"]
    state = lambda key: text["on" if flags.getboolean(key) else "off"]
    logger = logging.getLogger("main")
    logger.info(
        text["ready"].format(
            lots=len(cardinal.profile.get_lots()), plugins=len(cardinal.plugins)
        )
    )
    logger.info(
        text["features"].format(
            raise_=state("autoRaise"),
            response=state("autoResponse"),
            delivery=state("autoDelivery"),
        )
    )
    logger.info(text["files"])
