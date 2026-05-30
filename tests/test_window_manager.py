import logging

from monitorreminder.constants import APP_NAME
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


def test_find_window_prefers_matching_process_name(monkeypatch) -> None:
    manager = WindowManager(logging.getLogger("test-window-manager"))

    def fake_enum_windows(callback, extra) -> None:
        assert extra == 0
        for hwnd in [10, 20]:
            callback(hwnd, extra)

    monkeypatch.setattr("monitorreminder.window_manager.win32gui.EnumWindows", fake_enum_windows)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.IsWindowVisible", lambda hwnd: True)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.GetWindowText", lambda hwnd: "Target")
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.GetClassName", lambda hwnd: "Notepad")
    monkeypatch.setattr(manager, "_process_name", lambda hwnd: "foo.exe" if hwnd == 10 else "bar.exe")

    assert manager._find_window("Target", "Notepad", "bar.exe") == 20


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
    monkeypatch.setattr(manager, "_find_window", lambda title, class_name, process_name="": 99)
    monkeypatch.setattr(manager, "_is_window_maximized", lambda hwnd: False)
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


def test_restore_uses_exact_mode_when_monitor_signature_matches(monkeypatch) -> None:
    """When the current monitor layout matches the saved signature, restore uses
    the absolute pixel rect (exact mode) and not the proportional calculation."""
    manager = WindowManager(logging.getLogger("test-exact-mode"))
    monitor = MonitorSnapshot(name="Primary", x=0, y=0, width=1920, height=1080, is_primary=True)
    saved_signature = "0,0,1920,1080,1"

    # Saved absolute rect differs from where the proportional calculation would land
    # (absolute=50,60 vs proportional=192,216) — exact mode must use 50,60.
    profile = Profile(
        id=1,
        name="Exact",
        monitor_signature=saved_signature,
        windows=[
            WindowSnapshot(
                title="Editor",
                process_name="code.exe",
                class_name="Chrome_WidgetWin_1",
                rect=WindowRect(left=50, top=60, width=800, height=600),
                monitor_name="Primary",
                relative_rect=RelativeRect(x=0.1, y=0.2, width=0.5, height=0.5),
            )
        ],
    )
    placement_calls: list[tuple[int, int, int, int]] = []

    monkeypatch.setattr(manager, "monitor_snapshots", lambda: [monitor])
    monkeypatch.setattr(manager, "monitor_signature", lambda monitors=None: saved_signature)
    monkeypatch.setattr(manager, "_find_window", lambda title, class_name, process_name="": 99)
    monkeypatch.setattr(manager, "_is_window_maximized", lambda hwnd: False)
    # GetWindowRect: return out-of-position on first call (triggers restore), then the
    # target position on subsequent calls (simulates that SetWindowPlacement worked).
    rect_calls = [0]
    def fake_get_rect(hwnd):
        rect_calls[0] += 1
        return (0, 0, 400, 300) if rect_calls[0] == 1 else (50, 60, 850, 660)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.GetWindowRect", fake_get_rect)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.ShowWindow", lambda hwnd, mode: None)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.SetWindowPos", lambda *a, **kw: None)
    monkeypatch.setattr(
        "monitorreminder.window_manager.win32gui.SetWindowPlacement",
        lambda hwnd, placement: placement_calls.append(placement[4]),
    )

    summary = manager.restore_profile(profile)

    # Exact mode must be selected.
    assert summary.restore_mode == "exact"
    assert summary.restored_count == 1
    # Coordinates must match the absolute saved rect (left, top, right, bottom).
    assert placement_calls == [(50, 60, 850, 660)]


def test_restore_uses_proportional_mode_when_monitor_signature_differs(monkeypatch) -> None:
    """When the monitor layout changed, restore recalculates positions proportionally."""
    manager = WindowManager(logging.getLogger("test-proportional-mode"))
    monitor = MonitorSnapshot(name="Primary", x=0, y=0, width=1920, height=1080, is_primary=True)
    saved_signature = "0,0,2560,1440,1"  # different from current

    profile = Profile(
        id=1,
        name="Proportional",
        monitor_signature=saved_signature,
        windows=[
            WindowSnapshot(
                title="Browser",
                process_name="chrome.exe",
                class_name="Chrome_WidgetWin_1",
                rect=WindowRect(left=256, top=288, width=1280, height=720),
                monitor_name="Primary",
                relative_rect=RelativeRect(x=0.1, y=0.2, width=0.5, height=0.5),
            )
        ],
    )
    # Proportional target: x=0.1*1920=192, y=0.2*1080=216, w=0.5*1920=960, h=0.5*1080=540
    placement_calls: list[tuple[int, int, int, int]] = []

    monkeypatch.setattr(manager, "monitor_snapshots", lambda: [monitor])
    monkeypatch.setattr(manager, "monitor_signature", lambda monitors=None: "0,0,1920,1080,1")
    monkeypatch.setattr(manager, "_find_window", lambda title, class_name, process_name="": 99)
    monkeypatch.setattr(manager, "_is_window_maximized", lambda hwnd: False)
    rect_calls = [0]
    def fake_get_rect(hwnd):
        rect_calls[0] += 1
        return (0, 0, 400, 300) if rect_calls[0] == 1 else (192, 216, 1152, 756)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.GetWindowRect", fake_get_rect)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.ShowWindow", lambda hwnd, mode: None)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.SetWindowPos", lambda *a, **kw: None)
    monkeypatch.setattr(
        "monitorreminder.window_manager.win32gui.SetWindowPlacement",
        lambda hwnd, placement: placement_calls.append(placement[4]),
    )

    summary = manager.restore_profile(profile)

    assert summary.restore_mode == "proportional"
    assert summary.restored_count == 1
    # Proportional on 1920x1080 as (left, top, right, bottom).
    assert placement_calls == [(192, 216, 1152, 756)]


def test_restore_uses_monitor_index_when_name_changes(monkeypatch) -> None:
    manager = WindowManager(logging.getLogger("test-monitor-index-fallback"))
    monitors = [
        MonitorSnapshot(name="Renamed-Primary", x=0, y=0, width=1920, height=1080, is_primary=True),
        MonitorSnapshot(name="Renamed-Secondary", x=1920, y=0, width=1920, height=1080, is_primary=False),
    ]

    profile = Profile(
        id=1,
        name="Desk",
        monitor_signature="0,0,1920,1080,1|1920,0,1920,1080,0",
        windows=[
            WindowSnapshot(
                title="Editor",
                process_name="code.exe",
                class_name="Chrome_WidgetWin_1",
                rect=WindowRect(left=2000, top=120, width=1000, height=700),
                monitor_name="Old-Secondary",
                monitor_index=1,
                relative_rect=RelativeRect(x=0.1, y=0.1, width=0.5, height=0.5),
            )
        ],
    )
    # Proportional target on index=1 monitor (x=1920): 1920+0.1*1920=2112, 0+0.1*1080=108, w=960, h=540
    placement_calls: list[tuple[int, int, int, int]] = []

    monkeypatch.setattr(manager, "monitor_snapshots", lambda: monitors)
    monkeypatch.setattr(manager, "monitor_signature", lambda monitors=None: "different")
    monkeypatch.setattr(manager, "_find_window", lambda title, class_name, process_name="": 99)
    monkeypatch.setattr(manager, "_is_window_maximized", lambda hwnd: False)
    rect_calls = [0]
    def fake_get_rect(hwnd):
        rect_calls[0] += 1
        return (0, 0, 400, 300) if rect_calls[0] == 1 else (2112, 108, 3072, 648)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.GetWindowRect", fake_get_rect)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.ShowWindow", lambda hwnd, mode: None)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.SetWindowPos", lambda *a, **kw: None)
    monkeypatch.setattr(
        "monitorreminder.window_manager.win32gui.SetWindowPlacement",
        lambda hwnd, placement: placement_calls.append(placement[4]),
    )

    summary = manager.restore_profile(profile)

    assert summary.restore_mode == "proportional"
    assert summary.restored_count == 1
    # Must restore on index=1 monitor (x starts at 1920), not on primary.
    assert placement_calls == [(2112, 108, 3072, 648)]


def test_restore_maximized_window_repositions_then_maximizes(monkeypatch) -> None:
    """A window saved as maximized must be placed at its normal rect on the correct monitor
    with SW_SHOWMAXIMIZED so Windows fills the right screen."""
    manager = WindowManager(logging.getLogger("test-maximized-restore"))
    monitors = [
        MonitorSnapshot(name="Primary", x=0, y=0, width=1920, height=1080, is_primary=True),
        MonitorSnapshot(name="Secondary", x=1920, y=0, width=1920, height=1080, is_primary=False),
    ]
    saved_signature = "0,0,1920,1080,1|1920,0,1920,1080,0"

    # Window was maximized on Secondary; rect is the *normal* (pre-maximize) position.
    profile = Profile(
        id=1,
        name="Desk",
        monitor_signature=saved_signature,
        windows=[
            WindowSnapshot(
                title="Editor",
                process_name="code.exe",
                class_name="Chrome_WidgetWin_1",
                rect=WindowRect(left=1960, top=50, width=1200, height=700),
                monitor_name="Secondary",
                relative_rect=RelativeRect(x=0.02, y=0.046, width=0.625, height=0.648),
                is_maximized=True,
            )
        ],
    )

    placement_calls: list[tuple] = []

    monkeypatch.setattr(manager, "monitor_snapshots", lambda: monitors)
    monkeypatch.setattr(manager, "monitor_signature", lambda monitors=None: saved_signature)
    monkeypatch.setattr(manager, "_find_window", lambda title, class_name, process_name="": 99)
    # Window is currently maximized on Primary (moved there after monitor change).
    monkeypatch.setattr(manager, "_is_window_maximized", lambda hwnd: True)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.GetWindowRect", lambda hwnd: (0, 0, 1920, 1080))
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.ShowWindow", lambda hwnd, mode: None)
    monkeypatch.setattr("monitorreminder.window_manager.win32gui.SetWindowPos", lambda *a, **kw: None)
    monkeypatch.setattr(
        "monitorreminder.window_manager.win32gui.SetWindowPlacement",
        lambda hwnd, placement: placement_calls.append(placement),
    )

    summary = manager.restore_profile(profile)

    import win32con as _w
    assert summary.restored_count == 1
    assert summary.failed_count == 0
    # SetWindowPlacement must use SW_SHOWMAXIMIZED and the normal rect on Secondary monitor.
    assert len(placement_calls) == 1
    assert placement_calls[0][1] == _w.SW_SHOWMAXIMIZED
    assert placement_calls[0][4] == (1960, 50, 3160, 750)  # (left, top, right, bottom)


def test_restore_skips_monitorreminder_window(monkeypatch) -> None:
    manager = WindowManager(logging.getLogger("test-skip-app-window"))
    monitor = MonitorSnapshot(name="Primary", x=0, y=0, width=1920, height=1080, is_primary=True)
    profile = Profile(
        id=1,
        name="Desk",
        windows=[
            WindowSnapshot(
                title=APP_NAME,
                process_name="MonitorReminder.exe",
                class_name="TkTopLevel",
                rect=WindowRect(left=100, top=100, width=900, height=650),
                monitor_name="Primary",
                relative_rect=RelativeRect(x=0.05, y=0.05, width=0.45, height=0.45),
            )
        ],
    )

    find_calls: list[str] = []
    monkeypatch.setattr(manager, "monitor_snapshots", lambda: [monitor])
    monkeypatch.setattr(manager, "_find_window", lambda title, class_name, process_name="": find_calls.append(title))

    summary = manager.restore_profile(profile)

    assert summary.restored_count == 0
    assert summary.missing_count == 0
    assert find_calls == []