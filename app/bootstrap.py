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
    from app.shutdown import coordinator

    shutdown = coordinator()
    shutdown.bind(cardinal)
    cardinal.init()
    shutdown.discover()
    if shutdown.requested.is_set():
        return
    from app.updates.health import mark_healthy

    mark_healthy(Path.cwd())
    log_ready(cardinal)
    cardinal.run()


def main() -> int:
    from app.shutdown import coordinator

    shutdown = coordinator()
    result = SUCCESS_EXIT_CODE
    try:
        prepare_environment()
        from app.stop_control import stop_requested, watch_stop_requests

        if stop_requested(Path.cwd()):
            shutdown.request(manual=True)
        else:
            watch_stop_requests(Path.cwd())
            from app.console_status import runtime_banner

            if Path(MAIN_CONFIG).exists():
                runtime_banner()
            logging.getLogger("main").info("%s v%s", PROJECT_NAME, VERSION)
            if not Path(MAIN_CONFIG).exists():
                first_setup()
            else:
                run_cardinal()
    except KeyboardInterrupt:
        if not shutdown.requested.is_set():
            from app.stop_control import acknowledge_manual_stop

            acknowledge_manual_stop(Path.cwd())
            shutdown.request(manual=True)
        logging.getLogger("main").info("%s завершает работу", PROJECT_NAME)
    except Exception as error:
        logging.getLogger("main").error(
            "%s failed: %s", PROJECT_NAME, type(error).__name__
        )
        logging.getLogger("main").debug("TRACEBACK", exc_info=True)
        result = FAILURE_EXIT_CODE
    finally:
        from Utils.logger import stop_logging

        shutdown.finish()
        stop_logging()
    if shutdown.restart_pending():
        try:
            shutdown.execute_restart()
        except OSError as error:
            from Utils.logger import configure_logging

            configure_logging()
            logging.getLogger("main").error("Перезапуск не выполнен (%s)", type(error).__name__)
            stop_logging()
            return FAILURE_EXIT_CODE
    return shutdown.exit_code(result)
