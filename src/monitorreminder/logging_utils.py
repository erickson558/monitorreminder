from __future__ import annotations

import logging

from monitorreminder.paths import log_path


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("monitorreminder")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path(), encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger