from locales import ru


def __getattr__(name):
    return getattr(ru, name)


def __dir__():
    return dir(ru)
