---
name: windows-layout-validation
description: 'Use for validating monitor detection, window profile capture logic, restore math, and Windows packaging assumptions in this project.'
argument-hint: 'Describe the layout behavior or monitor scenario to validate'
user-invocable: true
---

# Windows Layout Validation

## When to Use
- Checking monitor-aware profile behavior
- Reviewing restore logic after backend changes
- Verifying Windows-specific assumptions before packaging

## Procedure
1. Inspect `src/monitorreminder/window_manager.py` and related tests.
2. Validate monitor-relative math with the narrowest test possible.
3. Run a smoke import or packaging-oriented check when the touched code affects startup.
4. Document any Windows API limitation or fallback behavior.