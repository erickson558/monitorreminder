from monitorreminder.models import MonitorSnapshot, RelativeRect
from monitorreminder.window_manager import WindowManager
import logging


def test_relative_rect_restores_with_expected_dimensions() -> None:
    monitor = MonitorSnapshot(name="Primary", x=0, y=0, width=1920, height=1080, is_primary=True)
    relative = RelativeRect(x=0.1, y=0.2, width=0.5, height=0.5)
    left = int(monitor.x + (relative.x * monitor.width))
    top = int(monitor.y + (relative.y * monitor.height))
    width = int(relative.width * monitor.width)
    height = int(relative.height * monitor.height)
    assert (left, top, width, height) == (192, 216, 960, 540)


def test_monitor_signature_is_stable_when_monitor_order_changes() -> None:
    manager = WindowManager(logging.getLogger("test-signature"))
    monitors_a = [
        MonitorSnapshot(name="SECOND", x=1920, y=0, width=1920, height=1080, is_primary=False),
        MonitorSnapshot(name="PRIMARY", x=0, y=0, width=1920, height=1080, is_primary=True),
    ]
    monitors_b = [
        MonitorSnapshot(name="PRIMARY-RENAMED", x=0, y=0, width=1920, height=1080, is_primary=True),
        MonitorSnapshot(name="SECOND-RENAMED", x=1920, y=0, width=1920, height=1080, is_primary=False),
    ]

    assert manager.monitor_signature(monitors_a) == manager.monitor_signature(monitors_b)