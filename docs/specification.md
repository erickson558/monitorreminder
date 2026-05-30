# MonitorReminder Specification

## Goal

Create a Windows desktop utility that remembers and restores application window layouts across multiple monitor configurations.

## Functional requirements

1. The application stores up to five named profiles.
2. Each profile stores the visible window list, their sizes, and their positions relative to a monitor.
3. The UI persists automatically to `config.json` on every relevant change.
4. The UI remembers window size, position, window state (normal/maximized), selected language, auto-start preference, and auto-close settings.
5. The UI includes a visible status area, version, Exit action, About action, and PayPal support button.
6. The UI supports Spanish and English.
7. The monitor watcher runs without freezing the UI.
8. The application writes timestamped logs to `log.txt`.
9. Window finding uses a three-pass fuzzy strategy: exact title match, best shared trailing segment on `" - "` title parts (handles VSCode, Edge, Brave, Foxit PDF, Postman, and similar apps whose titles include a dynamic prefix), then unique class+process candidate.
10. When a `SetWindowPos` or `SetWindowPlacement` call is silently blocked by UIPI (User Interface Privilege Isolation) because the target process runs elevated, the restore engine detects the failure, logs a warning with guidance to run as Administrator, and counts the window as failed rather than restored.
11. Window restoration uses `SetWindowPlacement` as the primary API (DPI-context-independent, handles UWP/`ApplicationFrameWindow`) with a three-step `SW_RESTORE` → `SetWindowPos` → state fallback.

## Non-functional requirements

1. The GUI must run as a Windows desktop app without a console window when packaged.
2. The codebase separates GUI concerns from monitor and window management.
3. Packaging uses the local icon file.
4. The packaged executable is generated in the `dist/` folder by PyInstaller and copied or published via GitHub Actions.
5. Release automation uses GitHub Actions and semantic version tags.
6. Packaging or release workflow changes must update the repository documentation used in GitHub.

## Acceptance checks

1. Unit tests validate config persistence defaults and monitor-relative layout math.
2. A smoke import of the main package succeeds in Python 3.12.
3. Restoring a profile does not fail when a matching window is found during `EnumWindows` enumeration.
4. Restoring a profile does not move windows that already match the selected profile within tolerance, and the UI reports that the profile is already applied.
5. Packaging metadata matches application version `0.3.2`.
6. The documented build flow rebuilds with the local `.ico` file and produces `MonitorReminder.exe`.
7. `_find_window` locates a VSCode window whose title changed (different open file) by matching the shared `" - Visual Studio Code"` suffix segment — the window must not appear as missing in the restore summary.
8. `_find_window` locates an Edge or Brave window whose tab title changed by matching the shared `" - Microsoft Edge"` / `" - Brave"` suffix segment.
9. After calling `_restore_window`, if the window position did not change and the target process is elevated (admin), `restore_profile` increments `failed_count` and logs a warning containing "run as Administrator".
10. `_restore_window` calls `SetWindowPlacement` with the correct `showCmd` (`SW_SHOWNORMAL`, `SW_SHOWMAXIMIZED`, or `SW_SHOWMINIMIZED`) and the normal rect expressed as `(left, top, right, bottom)`.
11. All 14 unit tests pass with `pytest tests/ -v`.
