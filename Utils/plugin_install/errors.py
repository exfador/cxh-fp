class PluginInstallError(ValueError):
    def __init__(self, key, names=()):
        super().__init__(key)
        self.key = key
        self.names = tuple(names)
