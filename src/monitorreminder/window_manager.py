from __future__ import annotations

"""Capture and restore window layouts using Windows APIs and monitor-relative math."""

import ctypes
import ctypes.wintypes
import logging
import os
from dataclasses import replace
from datetime import datetime

import win32con
import win32gui
import win32process
from screeninfo import get_monitors

from monitorreminder.constants import APP_NAME
from monitorreminder.models import MonitorSnapshot, Profile, RelativeRect, RestoreSummary, WindowRect, WindowSnapshot

RECT_TOLERANCE = 12

# Class names that belong to UWP/Store apps hosted by ApplicationFrameHost.
_UWP_CLASS_NAMES = {"ApplicationFrameWindow"}

# Process names that typically run elevated and will be blocked by UIPI.
_KNOWN_ELEVATED_PROCESSES = {"Taskmgr.exe", "taskmgr.exe"}


def _shared_suffix_count(parts1: list[str], parts2: list[str]) -> int:
    """Count matching segments from the end of two title-segment lists."""
    count = 0
    for seg1, seg2 in zip(reversed(parts1), reversed(parts2)):
        if seg1.strip() == seg2.strip():
            count += 1
        else:
            break
    return count

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
        """Capture top-level windows (normal, minimized, and maximized) with monitor-relative positions.

        For minimized and maximized windows the saved rect is the *normal* (pre-minimize /
        pre-maximize) rectangle obtained from GetWindowPlacement.rcNormalPosition.  This
        ensures that restore can place every window at a sensible position on the correct
        monitor regardless of what state the window was in at capture time.
        """
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

            # Detect maximized state and retrieve the normal (non-minimized,
            # non-maximized) position via GetWindowPlacement.rcNormalPosition.
            is_maximized = False
            normal_pos: tuple[int, int, int, int] | None = None
            try:
                placement = win32gui.GetWindowPlacement(hwnd)
                # placement[1] is showCmd: SW_SHOWMAXIMIZED=3
                is_maximized = (not is_minimized) and (placement[1] == win32con.SW_SHOWMAXIMIZED)
                nr = placement[4]  # rcNormalPosition
                if len(nr) == 4 and nr[2] > nr[0] and nr[3] > nr[1]:
                    normal_pos = (int(nr[0]), int(nr[1]), int(nr[2]), int(nr[3]))
            except Exception:
                pass

            # Always store the *normal* rect so restore can position the window
            # correctly before re-applying the minimized/maximized state.
            if (is_minimized or is_maximized) and normal_pos is not None:
                left, top, right, bottom = normal_pos
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
                    is_maximized=is_maximized,
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
            current_is_maximized = self._is_window_maximized(hwnd)

            # For maximized windows target_rect holds the *normal* rect, while
            # GetWindowRect returns the maximized rect — they never match, so
            # maximized windows are always re-positioned to the correct monitor.
            if (
                self._window_matches_target(hwnd, target_rect)
                and current_is_minimized == window.is_minimized
                and current_is_maximized == window.is_maximized
            ):
                summary.already_aligned_count += 1
                continue
            try:
                self._restore_window(hwnd, target_rect, window.is_minimized, window.is_maximized)

                # Verify the window actually moved; silently-blocked UIPI calls
                # succeed at the API level but leave the window in place.
                if not window.is_maximized and not window.is_minimized:
                    if not self._window_matches_target(hwnd, target_rect):
                        if self._is_process_elevated(hwnd):
                            self.logger.warning(
                                "Skipped elevated window '%s' (%s) — run as Administrator to move it",
                                window.title, window.process_name,
                            )
                        else:
                            self.logger.warning(
                                "Window '%s' did not reach target position after restore",
                                window.title,
                            )
                        summary.failed_count += 1
                        continue

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
        """Locate a visible top-level window matching the stored identity.

        Three-pass strategy to handle apps with dynamic titles (VSCode, Edge,
        Brave, Foxit PDF, Postman, etc.):

        1. Exact: title + class_name + process_name.
        2. Suffix match: class_name + process_name + best shared trailing
           segment of the title split by \" - \" (e.g. \"Visual Studio Code\"
           in \"file.py - project - Visual Studio Code\").
        3. Unique candidate: class_name + process_name match when only one
           window of that identity exists (title changed completely).
        """
        candidates: list[tuple[int, str]] = []

        def callback(hwnd: int, _: int) -> bool:
            try:
                if not win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                    return True
                if win32gui.GetClassName(hwnd) != class_name:
                    return True
                if process_name and process_name != "unknown":
                    if self._process_name(hwnd) != process_name:
                        return True
                current_title = win32gui.GetWindowText(hwnd).strip()
                if current_title:
                    candidates.append((hwnd, current_title))
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(callback, 0)
        except Exception:
            pass

        if not candidates:
            return None

        # Pass 1: exact title
        for hwnd, current_title in candidates:
            if current_title == title:
                return hwnd

        # Pass 2: best trailing-segment match on " - " parts
        if title:
            saved_parts = title.split(" - ")
            best_hwnd: int | None = None
            best_score = 0
            for hwnd, current_title in candidates:
                score = _shared_suffix_count(saved_parts, current_title.split(" - "))
                if score > best_score:
                    best_score = score
                    best_hwnd = hwnd
            if best_score >= 1:
                self.logger.debug(
                    "Fuzzy-matched '%s' → '%s' (shared suffix segments: %d)",
                    title, dict(candidates).get(best_hwnd, "?"), best_score,
                )
                return best_hwnd

        # Pass 3: unique candidate (only one window of this class+process)
        if len(candidates) == 1:
            self.logger.debug(
                "Fuzzy-matched '%s' → '%s' (unique class+process candidate)",
                title, candidates[0][1],
            )
            return candidates[0][0]

        return None

    def _restore_window(
        self,
        hwnd: int,
        target_rect: WindowRect,
        is_minimized: bool,
        is_maximized: bool,
    ) -> None:
        """Move and resize a window to target_rect, then re-apply its saved state.

        Uses SetWindowPlacement (which is DPI-context-independent and handles
        UWP/ApplicationFrameWindow better than SetWindowPos) and falls back to
        the classic SW_RESTORE → SetWindowPos sequence when placement fails.
        """
        show_cmd = (
            win32con.SW_SHOWMAXIMIZED if is_maximized
            else win32con.SW_SHOWMINIMIZED if is_minimized
            else win32con.SW_SHOWNORMAL
        )
        normal_right = target_rect.left + target_rect.width
        normal_bottom = target_rect.top + target_rect.height

        placed = False
        try:
            win32gui.SetWindowPlacement(hwnd, (
                0,          # flags
                show_cmd,
                (-1, -1),   # ptMinPosition — keep default
                (-1, -1),   # ptMaxPosition — keep default
                (target_rect.left, target_rect.top, normal_right, normal_bottom),
            ))
            placed = True
        except Exception:
            pass

        if not placed:
            # Fallback: classic three-step restore.
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
            if is_maximized:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            elif is_minimized:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

    def _is_window_maximized(self, hwnd: int) -> bool:
        """Return True when the window is currently in the maximized state."""
        try:
            return bool(win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE) & win32con.WS_MAXIMIZE)
        except Exception:
            return False

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

    def _is_process_elevated(self, hwnd: int) -> bool:
        """Return True when the window's process runs with elevated (admin) privileges.

        An elevated target process blocks SetWindowPos calls from a non-elevated
        caller via UIPI (User Interface Privilege Isolation).  The call succeeds
        at the API level but the window does not move.
        """
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h_proc:
                # Cannot open the process handle — almost certainly elevated.
                return True
            TOKEN_QUERY = 0x0008
            h_token = ctypes.c_void_p()
            if not ctypes.windll.advapi32.OpenProcessToken(h_proc, TOKEN_QUERY, ctypes.byref(h_token)):
                ctypes.windll.kernel32.CloseHandle(h_proc)
                return True
            TOKEN_ELEVATION = 20
            elevation = ctypes.c_ulong(0)
            cb = ctypes.c_ulong(0)
            ctypes.windll.advapi32.GetTokenInformation(
                h_token, TOKEN_ELEVATION,
                ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(cb),
            )
            ctypes.windll.kernel32.CloseHandle(h_token)
            ctypes.windll.kernel32.CloseHandle(h_proc)
            return bool(elevation.value)
        except Exception:
            return False