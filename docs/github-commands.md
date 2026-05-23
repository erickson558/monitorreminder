# GitHub Commands

## Daily setup

```powershell
git init -b main
git add .
git commit -m "feat: bootstrap MonitorReminder V0.0.4"
gh repo create monitorreminder --public --source . --remote origin --push
```

- `git init -b main`: initializes the repository on the `main` branch.
- `git add .`: stages the current project files.
- `git commit -m "feat: bootstrap MonitorReminder V0.0.4"`: creates the first professional commit.
- `gh repo create ... --push`: creates the public GitHub repository and pushes the current branch.

## Release workflow

```powershell
git add .
git commit -m "fix: skip restore when selected profile is already applied (V0.0.4)"
git tag V0.0.4
git push origin main
git push origin V0.0.4
```

- Update `src/monitorreminder/constants.py`, `src/monitorreminder/__init__.py`, `pyproject.toml`, and `README.md` before creating the release commit.
- The GitHub Actions workflow builds the executable, runs tests, and publishes the release matching the in-app version.