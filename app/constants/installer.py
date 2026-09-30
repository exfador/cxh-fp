SUPPORTED_PYTHON = (3, 11)
SUPPORTED_PLATFORMS = ("win32", "linux", "darwin")
ENVIRONMENT_NAME = ".venv"
PYTHON_PATHS = {"win32": ("Scripts", "python.exe"), "posix": ("bin", "python")}
PROCESS_TIMEOUT = 1200
PROBE_TIMEOUT = 15
PYTHON_PROBE = "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))"
TERMINAL_WIDTH = 72
MINIMUM_WIDTH = 24
ANSI_CYAN = "\033[36m"
ANSI_GREEN = "\033[32m"
ANSI_RESET = "\033[0m"
MENU_STEPS = ("step_funpay", "step_telegram", "step_password", "step_connection")
