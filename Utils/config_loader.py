import configparser
import os
from configparser import ConfigParser, SectionProxy
from Utils.cardinal_tools import build_proxy, hash_password
from Utils.exceptions import (
    ConfigParseError,
    DuplicateSectionErrorWrapper,
    EmptyValueError,
    NoProductVarError,
    ParamNotFoundError,
    ProductsFileNotFoundError,
    SectionNotFoundError,
    SubCommandAlreadyExists,
    ValueNotValidError,
)
from Utils.text_encoding_normalizer import TextEncodingNormalizer
from app.constants.languages import SUPPORTED_LANGUAGES
from app.language_policy import migrate_removed_language
from app.brand_policy import migrate_brand_signature, migrate_message_templates
from app.config_store import write_config


def check_param(
    param_name: str,
    section: SectionProxy,
    valid_values: list[str | None] | None = None,
    raise_if_not_exists: bool = True,
) -> str | None:
    if param_name not in list(section.keys()):
        if raise_if_not_exists:
            raise ParamNotFoundError(param_name)
        return None
    value = section[param_name].strip()
    if not value:
        if valid_values and None in valid_values:
            return value
        raise EmptyValueError(param_name)
    if valid_values and valid_values != [None] and (value not in valid_values):
        raise ValueNotValidError(param_name, value, valid_values)
    return value


def create_config_obj(config_path: str) -> ConfigParser:
    config = ConfigParser(delimiters=(":",), interpolation=None)
    config.optionxform = str
    with open(config_path, "r", encoding="utf-8") as config_file:
        config.read_file(config_file)
    for section_name in config.sections():
        for parameter_name, parameter_value in config.items(section_name):
            config.set(
                section_name,
                parameter_name,
                TextEncodingNormalizer.normalize(parameter_value),
            )
    migrate_message_templates(config)
    return config


def load_main_config(config_path: str, persist_migrations: bool = True):
    config = create_config_obj(config_path)
    original = {section: dict(config[section]) for section in config.sections()}
    migrate_removed_language(config)
    migrate_brand_signature(config)
    values = {
        "FunPay": {
            "golden_key": "any",
            "user_agent": "any+empty",
            "autoRaise": ["0", "1"],
            "autoResponse": ["0", "1"],
            "autoDelivery": ["0", "1"],
            "multiDelivery": ["0", "1"],
            "autoRestore": ["0", "1"],
            "autoDisable": ["0", "1"],
            "oldMsgGetMode": ["0", "1"],
            "keepSentMessagesUnread": ["0", "1"],
            "locale": list(SUPPORTED_LANGUAGES),
        },
        "Telegram": {
            "enabled": ["0", "1"],
            "token": "any+empty",
            "secretKeyHash": "any",
            "proxy": "any+empty",
            "blockLogin": ["0", "1"],
        },
        "BlockList": {
            "blockDelivery": ["0", "1"],
            "blockResponse": ["0", "1"],
            "blockNewMessageNotification": ["0", "1"],
            "blockNewOrderNotification": ["0", "1"],
            "blockCommandNotification": ["0", "1"],
        },
        "NewMessageView": {
            "includeMyMessages": ["0", "1"],
            "includeFPMessages": ["0", "1"],
            "includeBotMessages": ["0", "1"],
            "notifyOnlyMyMessages": ["0", "1"],
            "notifyOnlyFPMessages": ["0", "1"],
            "notifyOnlyBotMessages": ["0", "1"],
            "showImageName": ["0", "1"],
        },
        "Greetings": {
            "ignoreSystemMessages": ["0", "1"],
            "onlyNewChats": ["0", "1"],
            "sendGreetings": ["0", "1"],
            "greetingsText": "any",
            "greetingsCooldown": "any",
        },
        "OrderConfirm": {
            "watermark": ["0", "1"],
            "sendReply": ["0", "1"],
            "replyText": "any",
        },
        "ReviewReply": {
            "star1Reply": ["0", "1"],
            "star2Reply": ["0", "1"],
            "star3Reply": ["0", "1"],
            "star4Reply": ["0", "1"],
            "star5Reply": ["0", "1"],
            "star1ReplyText": "any+empty",
            "star2ReplyText": "any+empty",
            "star3ReplyText": "any+empty",
            "star4ReplyText": "any+empty",
            "star5ReplyText": "any+empty",
        },
        "Proxy": {"enable": ["0", "1"], "proxy": "any+empty", "check": ["0", "1"]},
        "Other": {
            "watermark": "any+empty",
            "requestsDelay": [str(i) for i in range(1, 101)],
            "language": list(SUPPORTED_LANGUAGES),
        },
    }
    for section_name in values:
        if section_name not in config.sections():
            raise ConfigParseError(config_path, section_name, SectionNotFoundError())
        if section_name == "Greetings" and "cacheInitChats" in config[section_name]:
            config.remove_option(section_name, "cacheInitChats")
        for param_name in values[section_name]:
            if (
                section_name == "FunPay"
                and param_name == "oldMsgGetMode"
                and (param_name not in config[section_name])
            ):
                config.set("FunPay", "oldMsgGetMode", "0")
            elif (
                section_name == "Greetings"
                and param_name == "ignoreSystemMessages"
                and (param_name not in config[section_name])
            ):
                config.set("Greetings", "ignoreSystemMessages", "0")
            elif (
                section_name == "Other"
                and param_name == "language"
                and (param_name not in config[section_name])
            ):
                config.set("Other", "language", "ru")
            elif (
                section_name == "Other"
                and param_name == "language"
                and (config[section_name][param_name] == "eng")
            ):
                config.set("Other", "language", "en")
            elif (
                section_name == "Greetings"
                and param_name == "greetingsCooldown"
                and (param_name not in config[section_name])
            ):
                config.set("Greetings", "greetingsCooldown", "2")
            elif (
                section_name == "OrderConfirm"
                and param_name == "watermark"
                and (param_name not in config[section_name])
            ):
                config.set("OrderConfirm", "watermark", "1")
            elif (
                section_name == "FunPay"
                and param_name == "keepSentMessagesUnread"
                and (param_name not in config[section_name])
            ):
                config.set("FunPay", "keepSentMessagesUnread", "0")
            elif (
                section_name == "NewMessageView"
                and param_name == "showImageName"
                and (param_name not in config[section_name])
            ):
                config.set("NewMessageView", "showImageName", "1")
            elif (
                section_name == "Telegram"
                and param_name == "blockLogin"
                and (param_name not in config[section_name])
            ):
                config.set("Telegram", "blockLogin", "0")
            elif (
                section_name == "Telegram"
                and param_name == "secretKeyHash"
                and (param_name not in config[section_name])
            ):
                config.set(
                    section_name,
                    "secretKeyHash",
                    hash_password(config[section_name]["secretKey"]),
                )
                config.remove_option(section_name, "secretKey")
            elif (
                section_name == "FunPay"
                and param_name == "locale"
                and (param_name not in config[section_name])
            ):
                config.set(section_name, "locale", "ru")
            elif (
                section_name == "Greetings"
                and param_name == "onlyNewChats"
                and (param_name not in config[section_name])
            ):
                config.set("Greetings", "onlyNewChats", "0")
            elif (
                section_name == "Proxy"
                and param_name == "proxy"
                and (param_name not in config[section_name])
            ):
                if not (config["Proxy"]["ip"] and config["Proxy"]["port"]):
                    config.set("Proxy", "proxy", "")
                else:
                    config.set(
                        "Proxy",
                        "proxy",
                        build_proxy(
                            None,
                            config["Proxy"]["login"],
                            config["Proxy"]["password"],
                            config["Proxy"]["ip"],
                            config["Proxy"]["port"],
                        ),
                    )
                config.remove_option(section_name, "login")
                config.remove_option(section_name, "password")
                config.remove_option(section_name, "ip")
                config.remove_option(section_name, "port")
            elif (
                section_name == "Telegram"
                and param_name == "proxy"
                and (param_name not in config[section_name])
            ):
                config.set("Telegram", "proxy", "")
            try:
                if values[section_name][param_name] == "any":
                    check_param(param_name, config[section_name])
                elif values[section_name][param_name] == "any+empty":
                    check_param(param_name, config[section_name], valid_values=[None])
                else:
                    check_param(
                        param_name,
                        config[section_name],
                        valid_values=values[section_name][param_name],
                    )
            except (ParamNotFoundError, EmptyValueError, ValueNotValidError) as e:
                raise ConfigParseError(config_path, section_name, e)
    if persist_migrations and original != {
        section: dict(config[section]) for section in config.sections()
    }:
        write_config(config, config_path)
    return config


def load_auto_response_config(config_path: str):
    try:
        config = create_config_obj(config_path)
    except configparser.DuplicateSectionError as e:
        raise ConfigParseError(config_path, e.section, DuplicateSectionErrorWrapper())
    command_sets = []
    for command in config.sections():
        try:
            check_param("response", config[command])
            check_param(
                "telegramNotification",
                config[command],
                valid_values=["0", "1"],
                raise_if_not_exists=False,
            )
            check_param(
                "enabled",
                config[command],
                valid_values=["0", "1"],
                raise_if_not_exists=False,
            )
            check_param("notificationText", config[command], raise_if_not_exists=False)
        except (ParamNotFoundError, EmptyValueError, ValueNotValidError) as e:
            raise ConfigParseError(config_path, command, e)
        if not config.has_option(command, "enabled"):
            config.set(command, "enabled", "1")
        if "|" in command:
            command_sets.append(command)
    for command_set in command_sets:
        commands = command_set.split("|")
        parameters = config[command_set]
        for new_command in commands:
            new_command = new_command.strip()
            if not new_command:
                continue
            if new_command in config.sections():
                raise ConfigParseError(
                    config_path, command_set, SubCommandAlreadyExists(new_command)
                )
            config.add_section(new_command)
            for param_name in parameters:
                config.set(new_command, param_name, parameters[param_name])
    return config


def load_raw_auto_response_config(config_path: str):
    config = create_config_obj(config_path)
    for raw_commands in config.sections():
        if not config.has_option(raw_commands, "enabled"):
            config.set(raw_commands, "enabled", "1")
    return config


def load_auto_delivery_config(config_path: str):
    try:
        config = create_config_obj(config_path)
    except configparser.DuplicateSectionError as e:
        raise ConfigParseError(config_path, e.section, DuplicateSectionErrorWrapper())
    for lot_title in config.sections():
        try:
            lot_response = check_param("response", config[lot_title])
            products_file_name = check_param(
                "productsFileName", config[lot_title], raise_if_not_exists=False
            )
            check_param(
                "disable",
                config[lot_title],
                valid_values=["0", "1"],
                raise_if_not_exists=False,
            )
            check_param(
                "disableAutoRestore",
                config[lot_title],
                valid_values=["0", "1"],
                raise_if_not_exists=False,
            )
            check_param(
                "disableAutoDisable",
                config[lot_title],
                valid_values=["0", "1"],
                raise_if_not_exists=False,
            )
            check_param(
                "disableAutoDelivery",
                config[lot_title],
                valid_values=["0", "1"],
                raise_if_not_exists=False,
            )
            if products_file_name is None:
                continue
        except (ParamNotFoundError, EmptyValueError, ValueNotValidError) as e:
            raise ConfigParseError(config_path, lot_title, e)
        if not os.path.exists(f"storage/products/{products_file_name}"):
            raise ConfigParseError(
                config_path,
                lot_title,
                ProductsFileNotFoundError(f"storage/products/{products_file_name}"),
            )
        if "$product" not in lot_response:
            raise ConfigParseError(config_path, lot_title, NoProductVarError())
    return config
