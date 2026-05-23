# Changelog

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