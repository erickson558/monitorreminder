from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def config_path() -> Path:
    return app_root() / "config.json"


def log_path() -> Path:
    return app_root() / "log.txt"


def icon_path() -> Path:
    return app_root() / "network_25845.ico"