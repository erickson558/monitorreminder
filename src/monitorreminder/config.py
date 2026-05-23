from __future__ import annotations

"""Load and persist application settings next to the script or packaged executable."""

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

from monitorreminder.models import AppConfig, MonitorSnapshot, Profile, RelativeRect, UiSettings, WindowRect, WindowSnapshot
from monitorreminder.paths import config_path

T = TypeVar("T")


def _coerce_dataclass(cls: type[T], payload: dict[str, Any]) -> T:
    """Rebuild nested dataclasses from plain JSON dictionaries."""
    values: dict[str, Any] = {}
    type_hints = get_type_hints(cls)
    for field_info in fields(cls):
        value = payload.get(field_info.name)
        if value is None:
            continue
        field_type = type_hints.get(field_info.name, field_info.type)
        origin = get_origin(field_type)
        if is_dataclass(field_type):
            values[field_info.name] = _coerce_dataclass(field_type, value)
            continue
        if origin is list:
            item_type = get_args(field_type)[0]
            if is_dataclass(item_type):
                values[field_info.name] = [_coerce_dataclass(item_type, item) for item in value]
            else:
                values[field_info.name] = list(value)
            continue
        values[field_info.name] = value
    return cls(**values)


def default_profiles() -> list[Profile]:
    """Create the fixed set of five user profiles expected by the UI."""
    return [Profile(id=index, name=f"Profile {index}") for index in range(1, 6)]


def load_config(path: Path | None = None) -> AppConfig:
    """Load persisted settings, or return a default configuration on first run."""
    selected_path = path or config_path()
    if not selected_path.exists():
        return AppConfig(profiles=default_profiles())
    raw = json.loads(selected_path.read_text(encoding="utf-8"))
    config = _coerce_dataclass(AppConfig, raw)
    if not config.profiles:
        config.profiles = default_profiles()
    while len(config.profiles) < 5:
        next_index = len(config.profiles) + 1
        config.profiles.append(Profile(id=next_index, name=f"Profile {next_index}"))
    return config


def save_config(config: AppConfig, path: Path | None = None) -> None:
    """Persist configuration changes immediately to support auto-save behavior."""
    selected_path = path or config_path()
    selected_path.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")