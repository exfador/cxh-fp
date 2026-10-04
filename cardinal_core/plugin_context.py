from contextlib import contextmanager
from contextvars import ContextVar

ACTIVE_PLUGIN = ContextVar("cxh_active_plugin", default=None)


def active_plugin():
    return ACTIVE_PLUGIN.get()


@contextmanager
def plugin_owner(uuid):
    token = ACTIVE_PLUGIN.set(uuid)
    try:
        yield
    finally:
        ACTIVE_PLUGIN.reset(token)


def module_matches(module, prefixes):
    module = module or ""
    return any(
        module == prefix or module.startswith(prefix + ".") for prefix in prefixes
    )
