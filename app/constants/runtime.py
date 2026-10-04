from pathlib import Path
from app.constants.branding import SERVICE_NAME

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION = "1.1.9"
MAIN_CONFIG = "configs/_main.cfg"
DELIVERY_CONFIG = "configs/auto_delivery.cfg"
RESPONSE_CONFIG = "configs/auto_response.cfg"
DIRECTORIES = (
    "configs",
    "logs",
    "storage/cache",
    "storage/plugins",
    "storage/products",
    "plugins",
    "run",
)
SERVICE_FLAG = "COXERHUB_IS_RUNNING_AS_SERVICE"
SERVICE_PID_DIRECTORY = Path("/run") / SERVICE_NAME
FAILURE_EXIT_CODE = 1
SUCCESS_EXIT_CODE = 0
