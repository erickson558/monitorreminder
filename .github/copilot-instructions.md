# MonitorReminder Copilot Instructions

- Keep GUI logic in `src/monitorreminder/app.py` and OS-specific behavior in backend modules.
- Update `docs/specification.md` and focused tests before or with behavior changes.
- Keep version fields synchronized across `src/monitorreminder/constants.py`, `src/monitorreminder/__init__.py`, `pyproject.toml`, `README.md`, and `CHANGELOG.md`.
- Prefer targeted pytest runs or smoke imports over broad validation.