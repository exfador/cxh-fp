import functools
import importlib
import inspect
import subprocess
import sys

import urllib3.util.ssl_ as ssl_utils
from urllib3.util.retry import Retry

LEGACY_DEFAULT_CIPHERS = ":".join(
    (
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
    )
)
MISSING = object()


def pip_main(args=None) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pip", *(args or ())],
        check=False,
    )
    importlib.invalidate_caches()
    return result.returncode


def legacy_retry_init(original):
    @functools.wraps(original)
    def init(self, *args, method_whitelist=MISSING, **kwargs):
        if method_whitelist is not MISSING:
            kwargs.setdefault("allowed_methods", method_whitelist)
        original(self, *args, **kwargs)

    init.cxh_compat = True
    return init


def install_urllib3_compat():
    if not hasattr(Retry, "DEFAULT_METHOD_WHITELIST"):
        Retry.DEFAULT_METHOD_WHITELIST = Retry.DEFAULT_ALLOWED_METHODS
    if not hasattr(Retry, "BACKOFF_MAX"):
        Retry.BACKOFF_MAX = Retry.DEFAULT_BACKOFF_MAX
    if not hasattr(Retry, "method_whitelist"):
        Retry.method_whitelist = property(lambda self: self.allowed_methods)
    if not hasattr(ssl_utils, "DEFAULT_CIPHERS"):
        ssl_utils.DEFAULT_CIPHERS = LEGACY_DEFAULT_CIPHERS
    parameters = inspect.signature(Retry.__init__).parameters
    if "method_whitelist" not in parameters and not getattr(
        Retry.__init__, "cxh_compat", False
    ):
        Retry.__init__ = legacy_retry_init(Retry.__init__)


def install():
    install_urllib3_compat()
