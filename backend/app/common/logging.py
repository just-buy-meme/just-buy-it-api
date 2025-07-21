import logging
import os
from logging.handlers import RotatingFileHandler

ENV = os.getenv("APP_ENV", "dev")
LOG_FILE = f"logs/app_{ENV}.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()


LOG_FORMAT = "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)
file_handler.setLevel(getattr(logging, LOG_LEVEL))
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL))
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL), handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)
logger.info(f"Logging initialized in {ENV} environment.")
logger.debug("Debug message")
