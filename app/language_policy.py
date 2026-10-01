from app.constants.languages import (
    DEFAULT_LANGUAGE,
    LANGUAGE_CONFIG_FIELDS,
    REMOVED_LANGUAGE,
)
from app.config_store import write_config


def migrate_removed_language(config, config_path=None):
    changed = False
    for section, field in LANGUAGE_CONFIG_FIELDS:
        if config.get(section, field, fallback=None) != REMOVED_LANGUAGE:
            continue
        config.set(section, field, DEFAULT_LANGUAGE)
        changed = True
    if changed and config_path is not None:
        write_config(config, config_path)
    return changed
