# Redeemed_3D Printed Threads Calculator (Python)

A small Python app that reproduces the same thread-calculation logic from the provided HTML/JavaScript example, now with both **Metric** and **SAE** support.

## Features

- Metric mode: diameter + pitch inputs.
- SAE mode: diameter (inches) + TPI input.
- Dropdown to switch thread standard.
- Enlarged fixed-size window so all sections remain visible after calculations.

## Run the app

```bash
python3 thread_calculator.py
```

## Run tests

```bash
python3 -m unittest discover -s tests
```
