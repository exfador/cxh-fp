from app.constants.branding import PROJECT_NAME
import logging
from pathlib import Path
from app.configuration import load_configuration
from app.constants.runtime import (
    VERSION,
    MAIN_CONFIG,
    FAILURE_EXIT_CODE,
    SUCCESS_EXIT_CODE,
)
from app.environment import prepare_environment
from cardinal import Cardinal
from first_setup import first_setup


def run_cardinal() -> None:
    configuration = load_configuration()
    cardinal = Cardinal(
        configuration.main,
        configuration.delivery,
        configuration.response,
        configuration.raw_response,
        VERSION,
    )
    from app.console_status import log_ready

    cardinal.init()
    from app.updates.health import mark_healthy

    mark_healthy(Path.cwd())
    log_ready(cardinal)
    cardinal.run()


def main() -> int:
    try:
        prepare_environment()
        from app.console_status import runtime_banner

        if Path(MAIN_CONFIG).exists():
            runtime_banner()
        logging.getLogger("main").info("%s v%s", PROJECT_NAME, VERSION)
        if not Path(MAIN_CONFIG).exists():
            first_setup()
            return SUCCESS_EXIT_CODE
        run_cardinal()
        return SUCCESS_EXIT_CODE
    except KeyboardInterrupt:
        logging.getLogger("main").info("%s stopped by the user", PROJECT_NAME)
        return SUCCESS_EXIT_CODE
    except Exception as error:
        logging.getLogger("main").error(
            "%s failed: %s", PROJECT_NAME, type(error).__name__
        )
        logging.getLogger("main").debug("TRACEBACK", exc_info=True)
        return FAILURE_EXIT_CODE
    finally:
        from Utils.logger import stop_logging

        stop_logging()
