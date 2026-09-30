from app.constants.languages import (
    DEFAULT_LANGUAGE,
    LANGUAGE_CONFIG_FIELDS,
    REMOVED_LANGUAGE,
)


def migrate_removed_language(config, config_path):
    changed = False
    for section, field in LANGUAGE_CONFIG_FIELDS:
        if config.get(section, field, fallback=None) != REMOVED_LANGUAGE:
            continue
        config.set(section, field, DEFAULT_LANGUAGE)
        changed = True
    if changed:
        with open(config_path, "w", encoding="utf-8") as config_file:
            config.write(config_file)
    return changed
