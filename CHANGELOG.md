# Changelog

## Unreleased

## V0.3.1

- Added `is_maximized` field to `WindowSnapshot` so the maximized/normal/minimized state is persisted per window.
- Capture now uses `GetWindowPlacement.rcNormalPosition` for both minimized **and** maximized windows, storing the pre-maximize normal rect instead of the full-screen maximized rect. This prevents `relative_rect > 1.0` values and ensures correct monitor assignment for maximized windows.
- Restore now re-applies the saved window state after repositioning: normal windows stay normal, minimized windows are re-minimized, and maximized windows are moved to the correct monitor's normal rect then re-maximized (`SW_MAXIMIZE`), so Windows fills the right screen.
- The "already aligned" skip check now also compares `is_maximized` state, ensuring maximized windows always get re-positioned to the correct monitor.

## V0.3.0

- Fixed monitor assignment for maximized windows: `_find_monitor_with_index` now uses an x-only fallback when the strict (x, y) containment check fails due to the negative top coordinate that Windows uses for maximized window frames (-8 / -9 px). This eliminates `relative_rect.x > 1.0` captures that caused off-screen placement in proportional-mode restore.
- Added exception safety to `_find_window`: the enumeration callback now wraps all win32 calls in `try/except`, and a second guard wraps `EnumWindows` itself, preventing a single bad handle from crashing an entire profile restore.
- Auto-restore after monitor change now waits 3 seconds before restoring, giving Windows time to finish repositioning windows after the monitor event fires.

## V0.2.0

- Added overwrite confirmation dialog when saving a profile that already has captured windows, preventing accidental data loss.
- Added `validations` skill to document and standardise user-facing guard patterns (confirm dialogs, input guards, status-bar feedback).
- Reduced GUI lag while moving/resizing the main window by debouncing geometry persistence writes.
- Prevented overlapping auto-restore tasks when monitor events fire in quick succession.
- Excluded the MonitorReminder main window from capture/restore to avoid visual glitches while moving across displays.
- Added an opacity guard that keeps the main window at alpha 1.0 during monitor transitions.
- Applied a stronger command-center futuristic UI pass with neon rails, telemetry strip, and more distinctive labels.

## V0.1.0

- Futuristic UI refresh with a stronger visual hierarchy: command-center hero, stylized cards, clearer monitor readouts, and updated action styling.
- Added full window geometry persistence, including normal/maximized state restoration between sessions.
- Improved bilingual UI copy (ES/EN) for monitor info, automation guidance, and support messaging.
- Updated GUI skill guidance to include a reusable futuristic design direction.

## V0.0.4

- Dual restore mode: uses exact pixel coordinates when the monitor layout matches the saved signature; falls back to proportional placement when the display configuration has changed.
- Status bar now shows which mode was used (exact / proportional) after every restore.
- Added `restore_mode` field to `RestoreSummary` for programmatic inspection.
- Added GitHub push skill (`.github/skills/github-push/SKILL.md`) for consistent releases.
- Added `restore_mode_exact` and `restore_mode_proportional` i18n keys (ES & EN).

## V0.0.3

- Fixed the restore crash caused by aborting `EnumWindows` during saved-window lookup.
- Added a focused regression test covering stable window enumeration during restore.

## V0.0.2

- Added explanatory comments and docstrings to the core modules.
- Kept packaging, release, and version metadata aligned for the next automated release.

## V0.0.1

- Initial release with monitor-aware window profile capture and restore.
- Persistent configuration, logging, and bilingual desktop UI.
- PyInstaller packaging, GitHub workflow, and repository custom agents/skills.