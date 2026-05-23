import logging

from monitorreminder.models import MonitorSnapshot, Profile, RelativeRect, WindowRect, WindowSnapshot
from monitorreminder.window_manager import WindowManager


def test_find_window_returns_match_without_aborting_enum(monkeypatch) -> None:
    manager = WindowManager(logging.getLogger("test-window-manager"))

    def fake_enum_windows(callback, extra) -> None:
        assert extra == 0
        for hwnd in [10, 20, 30]:
            callback(hwnd, extra)

    monkeypatch.setattr("monitorreminder.window_manager.win32gui.EnumWindows", fake_enum_windows)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.IsWindowVisible", lambda hwnd: hwnd != 10)
    monkeypatch.setattr(
        "monitorreminder.window_manager.win32gui.GetWindowText",
        lambda hwnd: {20: "Target", 30: "Other"}.get(hwnd, ""),
    )
    monkeypatch.setattr(
        "monitorreminder.window_manager.win32gui.GetClassName",
        lambda hwnd: {20: "CabinetWClass", 30: "Notepad"}.get(hwnd, ""),
    )

    assert manager._find_window("Target", "CabinetWClass") == 20


def test_restore_profile_skips_windows_that_already_match_target(monkeypatch) -> None:
    manager = WindowManager(logging.getLogger("test-window-manager"))
    monitor = MonitorSnapshot(name="Primary", x=0, y=0, width=1920, height=1080, is_primary=True)
    profile = Profile(
        id=1,
        name="Desk",
        windows=[
            WindowSnapshot(
                title="Target",
                process_name="notepad.exe",
                class_name="Notepad",
                rect=WindowRect(left=192, top=216, width=960, height=540),
                monitor_name="Primary",
                relative_rect=RelativeRect(x=0.1, y=0.2, width=0.5, height=0.5),
            )
        ],
    )
    set_window_pos_calls: list[tuple[int, int, int, int]] = []

    monkeypatch.setattr(manager, "monitor_snapshots", lambda: [monitor])
    monkeypatch.setattr(manager, "_find_window", lambda title, class_name: 99)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.GetWindowRect", lambda hwnd: (192, 216, 1152, 756))
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.ShowWindow", lambda hwnd, mode: None)
    monkeypatch.setattr(
        "monitorreminder.window_manager.win32gui.SetWindowPos",
        lambda hwnd, after, left, top, width, height, flags: set_window_pos_calls.append((left, top, width, height)),
    )

    summary = manager.restore_profile(profile)

    assert summary.is_already_aligned is True
    assert summary.restored_count == 0
    assert summary.already_aligned_count == 1
    assert summary.missing_count == 0
    assert summary.failed_count == 0
    assert set_window_pos_calls == []