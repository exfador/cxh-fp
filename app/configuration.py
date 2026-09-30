from dataclasses import dataclass
from configparser import ConfigParser

from Utils import config_loader
from app.constants.runtime import MAIN_CONFIG, RESPONSE_CONFIG, DELIVERY_CONFIG
from locales.localizer import Localizer


@dataclass(frozen=True)
class RuntimeConfiguration:
    main: ConfigParser
    delivery: ConfigParser
    response: ConfigParser
    raw_response: ConfigParser


def load_configuration() -> RuntimeConfiguration:
    main = config_loader.load_main_config(MAIN_CONFIG)
    Localizer(main["Other"]["language"])
    return RuntimeConfiguration(
        main,
        config_loader.load_auto_delivery_config(DELIVERY_CONFIG),
        config_loader.load_auto_response_config(RESPONSE_CONFIG),
        config_loader.load_raw_auto_response_config(RESPONSE_CONFIG),
    )
