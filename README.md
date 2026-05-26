# MonitorReminder

MonitorReminder is a Windows desktop application that captures and restores the layout of open windows across connected monitors. It stores up to five profiles, persists UI preferences automatically, and includes packaging and release automation for GitHub.

## Features

- Save up to five window layout profiles.
- Restore window layouts after monitor changes.
- Modern desktop UI with status bar, auto-close countdown, and non-blocking background tasks.
- Automatic persistence to `config.json` next to the Python entry point or packaged executable.
- English and Spanish interface support.
- Window and application logging to `log.txt`.
- PyInstaller packaging for a console-free Windows executable using the local `.ico` file.

## Requirements

- Windows 10 or newer
- Python 3.12+

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Build EXE

```powershell
.\scripts\build.ps1
```

The build uses the local `.ico` file from the project root and places the generated executable in the same folder as `main.py`, as `MonitorReminder.exe`.

## Project layout

- `main.py`: application entry point.
- `src/monitorreminder/`: application package.
- `.github/workflows/release.yml`: CI validation and release pipeline.
- `.github/agents/`: custom agents for this project.
- `.github/skills/`: reusable on-demand project skills.
- `docs/github-commands.md`: step-by-step Git and GitHub workflow.

## Versioning

This project uses semantic versioning with a `Vx.x.x` release tag format. The current version is `V0.1.0`.

## License

Apache License 2.0.

## Manual GitHub flow

See `docs/github-commands.md` for the exact Git, tag, and GitHub CLI commands used for daily work and releases.

When the packaging flow changes, update this README and the related GitHub docs in the same commit so the repository instructions stay consistent.