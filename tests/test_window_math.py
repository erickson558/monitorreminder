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


def test_find_monitor_with_index_handles_negative_top_maximized_windows() -> None:
    """Maximized windows on Windows have top=-8 or -9 (frame extends off-screen).
    The function must still assign them to the correct monitor using x-only matching."""
    manager = WindowManager(logging.getLogger("test-negative-top"))
    monitors = [
        MonitorSnapshot(name="DISPLAY1", x=0, y=0, width=1920, height=1080, is_primary=True),
        MonitorSnapshot(name="DISPLAY2", x=1920, y=0, width=1920, height=1080, is_primary=False),
    ]

    # Window maximized on DISPLAY2: left=1912 is still in DISPLAY1, but left=3832 is in DISPLAY2.
    # Both have top=-9 which fails the y-containment check.
    monitor_d1, idx_d1 = manager._find_monitor_with_index(1912, -9, monitors)
    assert monitor_d1.name == "DISPLAY1"
    assert idx_d1 == 0

    monitor_d2, idx_d2 = manager._find_monitor_with_index(3832, -9, monitors)
    assert monitor_d2.name == "DISPLAY2"
    assert idx_d2 == 1


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