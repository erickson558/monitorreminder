---
name: build-exe
description: "Use for compiling MonitorReminder.exe with PyInstaller. Ensures the correct .ico file (project root) is used, the output .exe lands beside main.py, and any running instance is stopped before rebuilding."
argument-hint: "Trigger when the user asks to compile, recompile, build, or generate the executable"
user-invocable: true
---

# Build EXE

## When to Use
- User asks to compile, recompile, build, or generate the executable
- After any source change that should ship as a new binary
- Before pushing a release or tag to GitHub

## Pre-build checks

Verify these assumptions are still true before running the build:

| Check | Expected value |
|---|---|
| Icon file | `network_25845.ico` exists in the project root beside `main.py` |
| `MonitorReminder.spec` → `icon=` | Points to `root / "network_25845.ico"` (resolved via `SPECPATH`) |
| `scripts\build.ps1` → `--distpath` | `.` (project root, beside `main.py`) |
| `scripts\build.ps1` → `--workpath` | `build` (intermediate artifacts only) |

If any check fails, fix it before proceeding.

## Procedure

### 1. Stop any running instance
The existing `MonitorReminder.exe` is locked by Windows while running. Kill it first.
```powershell
Get-Process MonitorReminder -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 2. Build
```powershell
Set-Location <project-root>
.\scripts\build.ps1
```

### 3. Verify the output
```powershell
Get-Item .\MonitorReminder.exe | Select-Object FullName, LastWriteTime
```
The `LastWriteTime` must be within the last few minutes.

### 4. Smoke-test the binary
```powershell
Start-Process .\MonitorReminder.exe
Start-Sleep -Seconds 3
Get-Process MonitorReminder -ErrorAction SilentlyContinue | Select-Object Name, Id
```
If the process appears, the build is healthy. Close it before continuing.

## What the spec produces
- `MonitorReminder.spec` uses `SPECPATH` to find the icon — no hard-coded absolute paths.
- `--distpath .` places `MonitorReminder.exe` beside `main.py` in the project root.
- `--workpath build` keeps intermediate PyInstaller artefacts in `build\MonitorReminder\`.
- The build is a one-file executable (`onefile`-style EXE via `a.binaries` + `a.datas` embedded).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `PermissionError` on `MonitorReminder.exe` | App is still running — run step 1 again |
| `FileNotFoundError: network_25845.ico` | Icon missing from project root; restore from git or add it back |
| `ModuleNotFoundError` at runtime | Add the module to `hiddenimports` in the spec and rebuild |
| `OneDrive` lock on `build\` folder | Use `--workpath` pointing outside OneDrive, e.g. `$env:TEMP\MRBuild` |
