# Changelog

## V0.0.4

- Added a pre-restore validation that skips moving windows already aligned with the selected profile.
- Added a clearer UI confirmation when the selected profile is already applied.

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