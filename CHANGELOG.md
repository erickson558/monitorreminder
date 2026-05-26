# Changelog

## Unreleased

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