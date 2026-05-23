# MonitorReminder Specification

## Goal

Create a Windows desktop utility that remembers and restores application window layouts across multiple monitor configurations.

## Functional requirements

1. The application stores up to five named profiles.
2. Each profile stores the visible window list, their sizes, and their positions relative to a monitor.
3. The UI persists automatically to `config.json` on every relevant change.
4. The UI remembers window size, position, selected language, auto-start preference, and auto-close settings.
5. The UI includes a visible status area, version, Exit action, About action, and PayPal support button.
6. The UI supports Spanish and English.
7. The monitor watcher runs without freezing the UI.
8. The application writes timestamped logs to `log.txt`.

## Non-functional requirements

1. The GUI must run as a Windows desktop app without a console window when packaged.
2. The codebase separates GUI concerns from monitor and window management.
3. Packaging uses the local icon file.
4. Release automation uses GitHub Actions and semantic version tags.

## Acceptance checks

1. Unit tests validate config persistence defaults and monitor-relative layout math.
2. A smoke import of the main package succeeds in Python 3.12.
3. Restoring a profile does not fail when a matching window is found during `EnumWindows` enumeration.
4. Restoring a profile does not move windows that already match the selected profile within tolerance, and the UI reports that the profile is already applied.
5. Packaging metadata matches application version `0.0.4`.