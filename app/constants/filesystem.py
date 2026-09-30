PRIVATE_PROCESS_MASK = 0o077
PRIVATE_FILE_MODE = 0o600
PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_STORAGE_DIRECTORIES = ("configs", "storage", "logs", "plugins", "run")
PRIVATE_STORAGE_FILES = ("backup.zip",)
PRIVATE_STORAGE_SYMLINK_ERROR = "Private storage cannot contain symbolic links"
