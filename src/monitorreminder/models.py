from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class WindowRect:
    left: int
    top: int
    width: int
    height: int


@dataclass(slots=True)
class RelativeRect:
    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True)
class MonitorSnapshot:
    name: str
    x: int
    y: int
    width: int
    height: int
    is_primary: bool


@dataclass(slots=True)
class WindowSnapshot:
    title: str
    process_name: str
    class_name: str
    rect: WindowRect
    monitor_name: str
    relative_rect: RelativeRect


@dataclass(slots=True)
class Profile:
    id: int
    name: str
    created_at: str | None = None
    monitor_signature: str = ""
    windows: list[WindowSnapshot] = field(default_factory=list)


@dataclass(slots=True)
class UiSettings:
    width: int = 1180
    height: int = 780
    pos_x: int = 120
    pos_y: int = 80
    language: str = "es"
    auto_start_monitoring: bool = True
    auto_close_enabled: bool = False
    auto_close_seconds: int = 60
    selected_profile: int = 1
    theme_mode: str = "dark"


@dataclass(slots=True)
class AppConfig:
    ui: UiSettings = field(default_factory=UiSettings)
    profiles: list[Profile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)