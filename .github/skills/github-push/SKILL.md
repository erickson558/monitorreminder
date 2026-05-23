---
name: github-push
description: "Use for pushing changes to GitHub, creating release tags, switching to the correct account (erickson558), and verifying workflow runs. Handles branch selection, version bumping, conventional commits, and release automation for this repository."
argument-hint: "Describe what to push: a bugfix, a minor feature, or a full release with tag"
user-invocable: true
---

# GitHub Push

## When to Use
- Publishing any change (bugfix, feature, release) to `https://github.com/erickson558/monitorreminder`
- Creating and pushing version tags
- Verifying that the GitHub Actions release workflow completed

## Procedure

### 1. Verify active account
```powershell
$env:GH_PAGER = ''
gh auth status
```
If the active account is not `erickson558`, switch it:
```powershell
gh auth switch -u erickson558
```

### 2. Rebuild the Windows executable consistently
Before committing a release or packaging-related change, rebuild with the project spec so the executable:
- uses the local `.ico` file stored in the repository root
- is generated in the same folder as `main.py` for a consistent local/release layout

```powershell
.\scripts\build.ps1
```

Validate these packaging assumptions before pushing:
- `MonitorReminder.spec` points `icon=` to the local icon file in the project root
- `scripts\build.ps1` keeps `--distpath .` so `MonitorReminder.exe` is created next to `main.py`

### 3. Verify clean state
```powershell
git status --short
```
If untracked or modified files are unexpected, stop and clarify before staging.

### 4. Update repository documentation when the packaging flow changes
If the build path, icon path, release steps, or output location changed, update the matching docs before staging:
- `README.md`
- `docs/specification.md`
- `docs/github-commands.md`
- `CHANGELOG.md` when the behavior is user-visible

### 5. Stage and commit
```powershell
git add .
git commit -m "<type>: <description> (V<X.X.X>)"
```
Conventional commit types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`.

### 6. Tag the version
```powershell
git tag V<X.X.X>
```

### 7. Push branch and tag
```powershell
git push origin main
git push origin V<X.X.X>
```

### 8. Verify the workflow
```powershell
$env:GH_PAGER = ''
gh run list --limit 3
```
Wait for the run to succeed, then check releases:
```powershell
$env:GH_PAGER = ''
gh release list --limit 5
```

## Version increment guide

| Change type          | Increment |
|----------------------|-----------|
| Bug fix              | patch     |
| New behaviour / feature | minor  |
| Breaking change      | major     |

Version must be consistent across:
- `src/monitorreminder/constants.py` (`APP_VERSION`)
- `src/monitorreminder/__init__.py` (`__version__`)
- `pyproject.toml` (`version`)
- `README.md`
- `CHANGELOG.md`

## Target branch
Always push to `main`. The GitHub Actions workflow in `.github/workflows/release.yml` triggers on every push to `main` and creates a release when a matching tag is present.

## Packaging consistency rule
- Keep the icon file local to the repository root and reference it from `MonitorReminder.spec`.
- Keep the executable output in the project root, beside `main.py`, by using `scripts\build.ps1`.
- If that packaging convention changes, update the docs in the same commit before pushing.
