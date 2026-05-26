---
name: validations
description: "Use when adding or reviewing user-facing validation guards in MonitorReminder: confirmation dialogs, input guards, and destructive-action protection."
argument-hint: "Describe the operation that needs a guard: overwrite, delete, rename, invalid input, etc."
user-invocable: true
---

# Validations

## When to Use
- Adding a confirmation dialog before a destructive or irreversible action
- Guarding inputs that must be non-empty, numeric, or within a valid range
- Reviewing whether existing flows have sufficient protection before shipping

## Guiding principles

### 1. Confirm before overwriting saved data
Any action that replaces previously persisted data (profile windows, profile name) must ask for confirmation when the destination already has content.

Use `tkinter.messagebox.askyesno()` with `parent=self` so the dialog is modal to the main window:

```python
from tkinter import messagebox

confirmed = messagebox.askyesno(
    self.t("confirm_overwrite_title"),
    self.t("confirm_overwrite_msg").format(name=profile.name),
    parent=self,
)
if not confirmed:
    self._set_status(self.t("status_overwrite_cancelled"))
    return
```

### 2. Only guard profiles that already have data
A profile with `profile.windows == []` is considered empty — capture it freely without asking.
Check `if profile.windows:` before showing the confirmation.

### 3. Translate every user-facing string
Never hardcode dialog titles or messages in English or Spanish.
Add all new strings to **both** `"es"` and `"en"` sections of `i18n.py`:

| Key | ES | EN |
|---|---|---|
| `confirm_overwrite_title` | ¿Sobrescribir escena? | Overwrite scene? |
| `confirm_overwrite_msg` | El perfil '{name}' ya tiene ventanas guardadas.\n¿Deseas sobrescribir la escena actual? | Profile '{name}' already has saved windows.\nDo you want to overwrite the current scene? |
| `status_overwrite_cancelled` | Captura cancelada — el perfil no fue modificado | Capture cancelled — profile was not modified |

### 4. Report the outcome in the status bar
After a cancelled or rejected validation, always call `self._set_status(...)` so the user gets feedback in the status bar rather than the UI silently doing nothing.

### 5. Numeric input guard pattern
For numeric fields (e.g., auto-close seconds) validate at the persistence boundary, not on every keystroke:

```python
raw = self.some_entry.get().strip()
if not raw.isdigit():
    self._set_status("...")   # or simply return silently
    return
value = max(MIN, min(MAX, int(raw)))
```

### 6. Keyboard shortcuts bypass the same guards
If an action is also bound to a keyboard shortcut (e.g., `<Control-s>`), the shortcut calls the same method — so the validation fires for both paths automatically. No special handling needed.

## Checklist when adding a new validation

- [ ] Guard fires for **both** the button click **and** any keyboard shortcut
- [ ] Cancellation sets a visible status-bar message
- [ ] New i18n keys added to `es` **and** `en`
- [ ] Empty/already-empty data skips the dialog (no confirmation for a no-op)
- [ ] Dialog uses `parent=self` so it is modal and centred on the main window

## Current guards in the codebase

| Method | Guard | Since |
|---|---|---|
| `save_selected_profile()` | Confirm before overwriting a profile that already has windows | V0.2.0 |
| `rename_selected_profile()` | Falls back to current name when the entry is empty (silent, no overwrite) | V0.1.0 |
| `_persist_auto_close_seconds()` | Skips persistence when the value is not a digit | V0.1.0 |
