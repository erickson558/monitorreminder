import logging

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