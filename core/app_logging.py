import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.database import APP_DIR

_LOGGER = None


def get_logger():
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logs_dir = APP_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "app.log"

    logger = logging.getLogger("kde_epson_fax")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _LOGGER = logger
    return logger
