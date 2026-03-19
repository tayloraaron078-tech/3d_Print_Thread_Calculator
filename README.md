# Redeemed Thread Calculator

A polished PySide6 desktop utility for sizing 3D printed metric and SAE threads. The calculation logic remains isolated from the Qt user interface so the app stays easy to test, maintain, and package.

## File structure

- `thread_calculator.py` — PySide6 `QMainWindow` application entry point, `.ui` loader, widget bindings, event handling, and dark-theme styling.
- `ui/main_window.ui` — Qt Designer-editable Qt Widgets layout for the main window, cards, inputs, results, and summary tiles.
- `thread_logic.py` — reusable thread parsing, calculation logic, and shared presets.
- `thread_calculator.pyw` — double-click friendly launcher for Windows environments.
- `tests/test_thread_calculator.py` — unit tests covering the calculation layer and shared presets.

## Requirements

```bash
pip install -r requirements.txt
```

### `requirements.txt`

```text
PySide6>=6.7,<7
```

## Run the app

```bash
python3 thread_calculator.py
```

## Open and edit the UI in Qt Designer

1. Launch Qt Designer.
2. Open `ui/main_window.ui`.
3. Edit the static Qt Widgets layout there and save the file.
4. Re-run `python3 thread_calculator.py`; `thread_calculator.py` loads the `.ui` at runtime with `QUiLoader`, so no code generation step is required.

## Migration notes

- The old `_build_ui()` method is now represented by `ui/main_window.ui` plus the `_load_ui()` / `_bind_widgets()` steps in `thread_calculator.py`.
- The old header, left-column control cards, result cards, and fit-guidance tiles were moved into the Designer file as named widgets and layouts.
- The old `LabeledInput`, `ResultRow`, and metric-tile construction code was replaced with widget-binding helpers that attach existing Designer widgets to the Python business logic.
- Calculation, validation, presets, status updates, copy/reset behavior, and styling all remain in Python.

## Run tests

```bash
python3 -m unittest discover -s tests
```

## Packaging note

The app is structured to work cleanly with tools such as PyInstaller later, because the business logic is separated from the user interface and the launcher has a single entry point.
