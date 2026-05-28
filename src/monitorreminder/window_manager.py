from __future__ import annotations

"""Capture and restore window layouts using Windows APIs and monitor-relative math."""

import logging
import os
from dataclasses import replace
from datetime import datetime
from typing import Callable

import win32con
import win32gui
import win32process
from screeninfo import get_monitors

from monitorreminder.constants import APP_NAME
from monitorreminder.models import MonitorSnapshot, Profile, RelativeRect, RestoreSummary, WindowRect, WindowSnapshot

RECT_TOLERANCE = 12

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
        """Generate a stable signature used by the watcher to detect display changes.

        The monitor API can return displays in varying order (and sometimes with
        inconsistent names), so we normalize by geometry and primary flag.
        """
        snapshots = sorted(
            monitors or self.monitor_snapshots(),
            key=lambda item: (item.x, item.y, item.width, item.height, int(item.is_primary), item.name),
        )
        return "|".join(
            f"{item.x},{item.y},{item.width},{item.height},{int(item.is_primary)}"
            for item in snapshots
        )

    def capture_profile(self, profile: Profile) -> Profile:
        """Capture top-level windows (normal and minimized) with monitor-relative positions."""
        monitors = self.monitor_snapshots()
        captured_windows: list[WindowSnapshot] = []

        def callback(hwnd: int, _: int) -> bool:
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == os.getpid():
                    return True
            except Exception:
                return True
            is_minimized = bool(win32gui.IsIconic(hwnd))
            if not win32gui.IsWindowVisible(hwnd) and not is_minimized:
                return True
            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return True
            class_name = win32gui.GetClassName(hwnd)
            if class_name in {"Shell_TrayWnd", "Progman", "WorkerW"}:
                return True
            if is_minimized:
                left, top, right, bottom = self._normal_rect_from_placement(hwnd) or win32gui.GetWindowRect(hwnd)
            else:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(right - left, 1)
            height = max(bottom - top, 1)
            monitor, monitor_index = self._find_monitor_with_index(left, top, monitors)
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
                    monitor_index=monitor_index,
                    is_minimized=is_minimized,
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

    def restore_profile(self, profile: Profile) -> RestoreSummary:
        """Restore saved windows using exact pixel positions when the monitor layout matches
        the saved signature, or proportional positions when the display configuration has changed."""
        monitors = self.monitor_snapshots()
        current_signature = self.monitor_signature(monitors)

        # Exact mode: the display layout is identical to when the profile was captured.
        # Proportional mode: one or more monitors changed size, position or name.
        use_exact = profile.monitor_signature == current_signature
        mode = "exact" if use_exact else "proportional"
        summary = RestoreSummary(profile_name=profile.name, restore_mode=mode)

        self.logger.info(
            "Restoring profile %s in %s mode (saved=%s current=%s)",
            profile.id, mode, profile.monitor_signature or "<none>", current_signature,
        )

        for window in profile.windows:
            if window.title == APP_NAME:
                continue
            hwnd = self._find_window(window.title, window.class_name, window.process_name)
            if not hwnd:
                summary.missing_count += 1
                continue
            monitor = self._select_monitor(window.monitor_name, window.monitor_index, monitors)

            # Build target rect according to the selected restore mode.
            if use_exact:
                # Use the absolute pixel rect captured at save time.
                target_rect = window.rect
            else:
                # Recalculate position proportionally relative to the current monitor dimensions.
                target_rect = self._target_rect(window, monitor)

            current_is_minimized = bool(win32gui.IsIconic(hwnd))

            if self._window_matches_target(hwnd, target_rect) and current_is_minimized == window.is_minimized:
                summary.already_aligned_count += 1
                continue
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOP,
                    target_rect.left,
                    target_rect.top,
                    target_rect.width,
                    target_rect.height,
                    win32con.SWP_SHOWWINDOW,
                )
                if window.is_minimized:
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                summary.restored_count += 1
            except Exception as exc:  # pragma: no cover
                summary.failed_count += 1
                self.logger.warning("Failed to restore window '%s': %s", window.title, exc)

        self.logger.info(
            "Restore summary for profile %s: mode=%s moved=%s aligned=%s missing=%s failed=%s",
            profile.id, mode,
            summary.restored_count,
            summary.already_aligned_count,
            summary.missing_count,
            summary.failed_count,
        )
        return summary

    def _find_monitor_with_index(self, left: int, top: int, monitors: list[MonitorSnapshot]) -> tuple[MonitorSnapshot, int]:
        """Find the monitor/index that currently contains a window origin point.

        Maximized windows on Windows extend ~8 px off-screen (top = -8 or -9), so a
        strict x-and-y containment check silently falls back to the primary monitor for
        every maximized window.  The x-only pass catches those cases correctly.
        """
        for index, monitor in enumerate(monitors):
            if monitor.x <= left < monitor.x + monitor.width and monitor.y <= top < monitor.y + monitor.height:
                return monitor, index

        # Maximized windows have a slightly negative top — match by x column only.
        for index, monitor in enumerate(monitors):
            if monitor.x <= left < monitor.x + monitor.width:
                return monitor, index

        primary_index = next((index for index, monitor in enumerate(monitors) if monitor.is_primary), 0)
        return monitors[primary_index], primary_index

    def _select_monitor(
        self,
        monitor_name: str,
        monitor_index: int | None,
        monitors: list[MonitorSnapshot],
    ) -> MonitorSnapshot:
        """Select the best target monitor for a saved window.

        Preference order: same monitor name, then saved index, then primary.
        """
        for monitor in monitors:
            if monitor.name == monitor_name:
                return monitor
        if monitor_index is not None and 0 <= monitor_index < len(monitors):
            return monitors[monitor_index]
        return next((monitor for monitor in monitors if monitor.is_primary), monitors[0])

    def _target_rect(self, window: WindowSnapshot, monitor: MonitorSnapshot) -> WindowRect:
        """Calculate the target absolute rectangle for a saved window on the selected monitor."""
        return WindowRect(
            left=int(monitor.x + (window.relative_rect.x * monitor.width)),
            top=int(monitor.y + (window.relative_rect.y * monitor.height)),
            width=max(int(window.relative_rect.width * monitor.width), 320),
            height=max(int(window.relative_rect.height * monitor.height), 180),
        )

    def _window_matches_target(self, hwnd: int, target_rect: WindowRect) -> bool:
        """Check whether the current window bounds already match the target within tolerance."""
        if win32gui.IsIconic(hwnd):
            left, top, right, bottom = self._normal_rect_from_placement(hwnd) or win32gui.GetWindowRect(hwnd)
        else:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        current_rect = WindowRect(
            left=left,
            top=top,
            width=max(right - left, 1),
            height=max(bottom - top, 1),
        )
        return (
            abs(current_rect.left - target_rect.left) <= RECT_TOLERANCE
            and abs(current_rect.top - target_rect.top) <= RECT_TOLERANCE
            and abs(current_rect.width - target_rect.width) <= RECT_TOLERANCE
            and abs(current_rect.height - target_rect.height) <= RECT_TOLERANCE
        )

    def _find_window(self, title: str, class_name: str, process_name: str = "") -> int | None:
        """Locate a visible top-level window matching the stored identity."""
        match: int | None = None

        def callback(hwnd: int, _: int) -> bool:
            nonlocal match
            try:
                if match is not None:
                    return True
                if not win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                    return True
                if win32gui.GetWindowText(hwnd).strip() == title and win32gui.GetClassName(hwnd) == class_name:
                    if process_name and process_name != "unknown" and self._process_name(hwnd) != process_name:
                        return True
                    match = hwnd
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(callback, 0)
        except Exception:
            pass
        return match

    def _normal_rect_from_placement(self, hwnd: int) -> tuple[int, int, int, int] | None:
        """Return the normal (restored) window rectangle when available."""
        try:
            placement = win32gui.GetWindowPlacement(hwnd)
            normal_rect = placement[4]
            if len(normal_rect) != 4:
                return None
            left, top, right, bottom = (int(value) for value in normal_rect)
            if right <= left or bottom <= top:
                return None
            return left, top, right, bottom
        except Exception:
            return None

    def _process_name(self, hwnd: int) -> str:
        """Resolve a friendly process name for UI display and logs."""
        if psutil is None:
            return "unknown"
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name()
        except Exception:
            return "unknown"