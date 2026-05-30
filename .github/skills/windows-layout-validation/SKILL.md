---
name: windows-layout-validation
description: 'Use for validating monitor detection, window profile capture logic, restore math, fuzzy window finding, and Windows packaging assumptions in this project.'
argument-hint: 'Describe the layout behavior or monitor scenario to validate'
user-invocable: true
---

# Windows Layout Validation

## When to Use
- Checking monitor-aware profile behavior
- Reviewing restore logic after backend changes
- Verifying Windows-specific assumptions before packaging
- Validating fuzzy window-finding behavior for apps with dynamic titles

## Key components

### `_find_window` — three-pass fuzzy strategy
Located in `src/monitorreminder/window_manager.py`.

| Pass | Match condition | Handles |
|---|---|---|
| 1 | Exact title + class_name + process_name | All apps (original behaviour) |
| 2 | Best shared trailing segment on `" - "` title parts | VSCode, Edge, Brave, Foxit PDF, Postman — apps with dynamic title prefixes |
| 3 | Unique candidate of same class + process | Apps that changed title completely |

When validating: confirm that a window captured as `"foo.py - project - Visual Studio Code"` is found when the current title is `"bar.py - other - Visual Studio Code"` (one shared suffix segment: `"Visual Studio Code"`).

### `_restore_window` — `SetWindowPlacement` primary, `SetWindowPos` fallback
`SetWindowPlacement` is called with `(flags=0, showCmd, ptMin=(-1,-1), ptMax=(-1,-1), rcNormalPosition=(left,top,right,bottom))`.
- `showCmd = SW_SHOWMAXIMIZED` (3) for maximized, `SW_SHOWMINIMIZED` (2) for minimized, `SW_SHOWNORMAL` (1) otherwise.
- Falls back to `SW_RESTORE → SetWindowPos → ShowWindow` when `SetWindowPlacement` raises.

### UIPI / elevation detection
After `_restore_window`, for non-maximized, non-minimized windows the engine reads back `GetWindowRect` and compares to the target within `RECT_TOLERANCE = 12 px`. If the position did not change **and** `_is_process_elevated` returns True, the window is counted as `failed` and a warning is logged. Elevated apps: `Taskmgr.exe`, Omen Gaming Hub, Hard Disk Sentinel, any UAC-elevated process.

To move elevated windows, MonitorReminder must itself run as Administrator.

## Procedure
1. Inspect `src/monitorreminder/window_manager.py` and related tests in `tests/test_window_manager.py`.
2. Validate monitor-relative math with the narrowest test possible.
3. For fuzzy-matching changes: add a test that confirms a renamed title is still found via suffix match.
4. For UIPI changes: mock `_is_process_elevated` and `GetWindowRect` to simulate a blocked move and assert `failed_count`.
5. Run `pytest tests/ -v` — all 14 tests must pass.
6. Document any new Windows API limitation or fallback behavior in `docs/specification.md` acceptance checks.
