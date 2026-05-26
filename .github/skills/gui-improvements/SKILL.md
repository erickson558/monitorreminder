---
name: gui-improvements
description: "Use when improving the MonitorReminder GUI: typography, spacing, colors, help text, and layout changes. Avoids the generic AI-generated look by enforcing opinionated visual patterns specific to this app."
argument-hint: "Describe the GUI area to improve: layout, colors, labels, help text, or a specific widget"
user-invocable: true
---

# GUI Improvements

## When to Use
- Changing layout, spacing, or visual hierarchy in `app.py`
- Improving or adding user-facing labels and instructions
- Making the app feel less generic / less AI-generated
- Adding new widgets, cards, or sections to the UI

## Guiding principles

### 0. Futuristic direction (default for this app)
When the user asks for a "futuristic" look, prefer this visual language:
- Deep navy + cyan palette with one green accent for positive actions
- "Command center" hierarchy: hero header, cards, and status rail
- Compact technical readouts for monitor info (monospace labels)
- Labels that feel like actions/scenes, not generic CRUD text

Avoid these in futuristic mode:
- Flat gray backgrounds and plain default buttons
- Overly rounded toy-like widgets
- Neon overload with poor contrast

### 1. Opinionated color palette
Do not use default customtkinter blue everywhere. Reserve it for secondary actions.
Use these consistently:

| Role | Light mode | Dark mode |
|---|---|---|
| Hero background | `#dbe8f8` | `#18263a` |
| Help/info card | `#d6edda` | `#0d2818` |
| Automation card | `#edf4fb` | `#102033` |
| Status bar | `#dfeaf7` | `#112338` |
| Destructive action | `#b03d3d` hover `#912e2e` | same |
| Primary profile selected | `#24706c` hover `#1f5c59` | same |

Always pass colors as a `(light, dark)` tuple — never a single hex string.

### 2. Typography
- Titles / section headers: `CTkFont("Segoe UI Semibold", 20, "bold")`
- Sub-headers / card titles: `CTkFont("Segoe UI Semibold", 13, "bold")`
- Body / hints: `CTkFont("Segoe UI", 12)` or `CTkFont("Segoe UI", 13)`
- App title: `CTkFont("Segoe UI Semibold", 30, "bold")`

### 3. Spacing
- Outer padding (window edge → frame): `padx=24, pady=24`
- Inner frame padding (frame edge → widget): `padx=16–20, pady=8–16`
- Between sibling widgets: `padx=8, pady=8`
- Corner radii: outer frames `28`, inner cards `18–24`

### 4. Labels must explain, not just name
Bad: `"Autocerrar"` — what does it close, when, why?
Good: `"Cerrar la app automáticamente después de: N segundos"`

How-to steps belong in the UI, not only in documentation.
Use numbered Unicode circles (①②③) for step sequences — they are compact and readable.

### 5. Avoid generic button labels
Bad: `"Guardar"`, `"Restaurar"`, `"Iniciar"`
Good: `"Guardar perfil"`, `"Restaurar perfil"`, `"Iniciar monitoreo"`
The label should describe the object being acted on.

### 6. Keep action buttons at the bottom of their section
Profile action buttons (`save`, `restore`, `rename`) belong below the profile cards, not above.
Destructive actions (`exit`) must have a distinct color (see palette above).

## Adding help text to the UI

Use a compact card (CTkFrame with `corner_radius=18`) with:
1. A bold title label (sub-header font)
2. A body CTkLabel with `justify="left"`, `wraplength=320`, body font
3. Newline-separated steps using ①②③

```python
howto_card = ctk.CTkFrame(parent, fg_color=("#d6edda", "#0d2818"), corner_radius=18)
howto_card.grid(row=N, column=0, padx=20, pady=(0, 16), sticky="ew")
howto_card.grid_columnconfigure(0, weight=1)
ctk.CTkLabel(howto_card, text=self.t("howto_title"),
             font=ctk.CTkFont("Segoe UI Semibold", 13, "bold"), anchor="w"
).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")
ctk.CTkLabel(howto_card, text=self.t("howto_steps"),
             justify="left", anchor="w", wraplength=320,
             font=ctk.CTkFont("Segoe UI", 12)
).grid(row=1, column=0, padx=14, pady=(0, 12), sticky="ew")
```

Translation keys (`i18n.py`) for the steps should use `\n` line breaks — CTkLabel renders them correctly.

## What NOT to do
- Do not add tooltips via third-party libraries (not in requirements.txt)
- Do not use `pack()` — the app uses `grid()` exclusively
- Do not hard-code pixel widths unless the widget has a fixed role (e.g., language dropdown `width=140`)
- Do not change `fg_color` to a single string — always use `(light, dark)` tuple

## Files to edit
- `src/monitorreminder/app.py` — layout and widgets
- `src/monitorreminder/i18n.py` — all visible text strings (both `es` and `en` must be updated together)

## Validation after changes
```powershell
# Verify the module loads without errors
python -c "import sys; sys.path.insert(0,'src'); from monitorreminder.app import MonitorReminderApp; print('OK')"
# Run all tests
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest tests/ -q
```
