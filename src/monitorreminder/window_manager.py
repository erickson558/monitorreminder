from __future__ import annotations

"""Capture and restore window layouts using Windows APIs and monitor-relative math."""

import logging
from dataclasses import replace
from datetime import datetime
from typing import Callable

import win32con
import win32gui
import win32process
from screeninfo import Monitor, get_monitors

from monitorreminder.models import MonitorSnapshot, Profile, RelativeRect, WindowRect, WindowSnapshot

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


class WindowManager:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def monitor_snapshots(self) -> list[MonitorSnapshot]:
        """Read the current monitor arrangement from Windows."""
        monitors = []
        for monitor in get_monitors():
            monitors.append(
                MonitorSnapshot(
                    name=getattr(monitor, "name", f"monitor-{monitor.x}-{monitor.y}"),
                    x=monitor.x,
                    y=monitor.y,
                    width=monitor.width,
                    height=monitor.height,
                    is_primary=monitor.is_primary,
                )
            )
        return monitors

    def monitor_signature(self, monitors: list[MonitorSnapshot] | None = None) -> str:
        """Generate a stable signature used by the watcher to detect display changes."""
        snapshots = monitors or self.monitor_snapshots()
        return "|".join(
            f"{item.name}:{item.x},{item.y},{item.width},{item.height},{int(item.is_primary)}"
            for item in snapshots
        )

    def capture_profile(self, profile: Profile) -> Profile:
        """Capture visible top-level windows and store their monitor-relative positions."""
        monitors = self.monitor_snapshots()
        captured_windows: list[WindowSnapshot] = []

        def callback(hwnd: int, _: int) -> bool:
            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return True
            class_name = win32gui.GetClassName(hwnd)
            if class_name in {"Shell_TrayWnd", "Progman", "WorkerW"}:
                return True
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(right - left, 1)
            height = max(bottom - top, 1)
            monitor = self._find_monitor(left, top, monitors)
            relative = RelativeRect(
                x=(left - monitor.x) / max(monitor.width, 1),
                y=(top - monitor.y) / max(monitor.height, 1),
                width=width / max(monitor.width, 1),
                height=height / max(monitor.height, 1),
            )
            process_name = self._process_name(hwnd)
            captured_windows.append(
                WindowSnapshot(
                    title=title,
                    process_name=process_name,
                    class_name=class_name,
                    rect=WindowRect(left=left, top=top, width=width, height=height),
                    monitor_name=monitor.name,
                    relative_rect=relative,
                )
            )
            return True

        win32gui.EnumWindows(callback, 0)
        self.logger.info("Captured %s windows for profile %s", len(captured_windows), profile.id)
        return replace(
            profile,
            created_at=datetime.now().isoformat(timespec="seconds"),
            monitor_signature=self.monitor_signature(monitors),
            windows=sorted(captured_windows, key=lambda item: (item.process_name.lower(), item.title.lower())),
        )

    def restore_profile(self, profile: Profile) -> int:
        """Restore the saved windows onto the closest matching current monitor layout."""
        monitors = self.monitor_snapshots()
        restored = 0
        for window in profile.windows:
            hwnd = self._find_window(window.title, window.class_name)
            if not hwnd:
                continue
            monitor = self._select_monitor(window.monitor_name, monitors)
            left = int(monitor.x + (window.relative_rect.x * monitor.width))
            top = int(monitor.y + (window.relative_rect.y * monitor.height))
            width = max(int(window.relative_rect.width * monitor.width), 320)
            height = max(int(window.relative_rect.height * monitor.height), 180)
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOP,
                    left,
                    top,
                    width,
                    height,
                    win32con.SWP_SHOWWINDOW,
                )
                restored += 1
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Failed to restore window '%s': %s", window.title, exc)
        self.logger.info("Restored %s windows from profile %s", restored, profile.id)
        return restored

    def _find_monitor(self, left: int, top: int, monitors: list[MonitorSnapshot]) -> MonitorSnapshot:
        """Find the monitor that currently contains a window origin point."""
        for monitor in monitors:
            if monitor.x <= left < monitor.x + monitor.width and monitor.y <= top < monitor.y + monitor.height:
                return monitor
        return next((monitor for monitor in monitors if monitor.is_primary), monitors[0])

    def _select_monitor(self, monitor_name: str, monitors: list[MonitorSnapshot]) -> MonitorSnapshot:
        """Prefer the saved monitor by name and fall back to the active primary monitor."""
        for monitor in monitors:
            if monitor.name == monitor_name:
                return monitor
        return next((monitor for monitor in monitors if monitor.is_primary), monitors[0])

    def _find_window(self, title: str, class_name: str) -> int | None:
        """Locate the first visible top-level window matching the stored identity."""
        match: int | None = None

        def callback(hwnd: int, _: int) -> bool:
            nonlocal match
            if match is not None:
                return True
            if not win32gui.IsWindowVisible(hwnd):
                return True
            if win32gui.GetWindowText(hwnd).strip() == title and win32gui.GetClassName(hwnd) == class_name:
                match = hwnd
            return True

        win32gui.EnumWindows(callback, 0)
        return match

    def _process_name(self, hwnd: int) -> str:
        """Resolve a friendly process name for UI display and logs."""
        if psutil is None:
            return "unknown"
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name()
        except Exception:
            return "unknown"