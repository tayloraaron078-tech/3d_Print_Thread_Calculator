# Redeemed Thread Calculator

A polished PySide6 desktop utility for sizing 3D printed metric and SAE threads. The calculation logic remains isolated from the Qt user interface so the app stays easy to test, maintain, and package.

## File structure

- `thread_calculator.py` — PySide6 `QMainWindow` application entry point, custom widgets, layout composition, and dark-theme styling.
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

## Run tests

```bash
python3 -m unittest discover -s tests
```

## Packaging note

The app is structured to work cleanly with tools such as PyInstaller later, because the business logic is separated from the user interface and the launcher has a single entry point.
