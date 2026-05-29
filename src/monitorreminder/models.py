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
    monitor_index: int | None = None
    is_minimized: bool = False
    is_maximized: bool = False


@dataclass(slots=True)
class Profile:
    id: int
    name: str
    created_at: str | None = None
    monitor_signature: str = ""
    windows: list[WindowSnapshot] = field(default_factory=list)


@dataclass(slots=True)
class RestoreSummary:
    profile_name: str
    restored_count: int = 0
    already_aligned_count: int = 0
    missing_count: int = 0
    failed_count: int = 0
    # 'exact' when monitor layout matches the saved signature, 'proportional' otherwise.
    restore_mode: str = "proportional"

    @property
    def is_already_aligned(self) -> bool:
        return (
            self.restored_count == 0
            and self.failed_count == 0
            and self.missing_count == 0
            and self.already_aligned_count > 0
        )


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
    window_state: str = "normal"


@dataclass(slots=True)
class AppConfig:
    ui: UiSettings = field(default_factory=UiSettings)
    profiles: list[Profile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)