"""3D print metric thread calculator.

Implements the same calculation logic as the provided HTML/JavaScript example
with a simple Tkinter interface and a reusable calculation function.
"""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


@dataclass
class ThreadCalculation:
    standard_tap_drill: float
    print_hole: float
    theoretical_bolt: float
    print_bolt: float
    min_layer: float
    max_layer: float


def calculate_thread_values(diameter: float, pitch: float) -> ThreadCalculation:
    """Calculate thread dimensions using the provided logic.

    Args:
        diameter: Nominal diameter (D), in mm.
        pitch: Thread pitch (P), in mm.

    Returns:
        ThreadCalculation values.

    Raises:
        ValueError: If diameter or pitch are not positive.
    """
    if diameter <= 0 or pitch <= 0:
        raise ValueError("Diameter and pitch must both be positive numbers.")

    # Theoretical ISO-style minor diameter estimate.
    theoretical_minor = diameter - (1.082532 * pitch)

    # Dynamic clearances from the original logic.
    hole_clearance = 0.2 if pitch < 1.5 else 0.3
    bolt_clearance = 0.2 if pitch < 1.5 else 0.35

    # Internal thread / hole calculations.
    standard_tap_drill = theoretical_minor + (pitch * 0.12)
    print_hole = standard_tap_drill + hole_clearance

    # External thread / bolt calculations.
    print_bolt = diameter - bolt_clearance

    # Layer-height guidance.
    min_layer = pitch * 0.1
    max_layer = pitch * 0.2

    return ThreadCalculation(
        standard_tap_drill=standard_tap_drill,
        print_hole=print_hole,
        theoretical_bolt=diameter,
        print_bolt=print_bolt,
        min_layer=min_layer,
        max_layer=max_layer,
    )


class ThreadCalculatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("3D Print Thread Calculator")
        self.root.geometry("620x430")
        self.root.resizable(False, False)

        self.diameter_var = tk.StringVar(value="8")
        self.pitch_var = tk.StringVar(value="1.25")

        self.theoretical_hole_var = tk.StringVar(value="-")
        self.print_hole_var = tk.StringVar(value="-")
        self.theoretical_bolt_var = tk.StringVar(value="-")
        self.print_bolt_var = tk.StringVar(value="-")
        self.layer_var = tk.StringVar(value="-")
        self.status_var = tk.StringVar(value="Enter values and press Calculate.")

        self._build_ui()
        self.calculate()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(frame, text="3D Print Metric Thread Calculator", font=("TkDefaultFont", 14, "bold"))
        title.pack(anchor="w", pady=(0, 12))

        inputs = ttk.Frame(frame)
        inputs.pack(fill="x", pady=(0, 10))

        ttk.Label(inputs, text="Nominal Diameter (mm)").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(inputs, textvariable=self.diameter_var, width=14).grid(row=0, column=1, sticky="w")

        ttk.Label(inputs, text="Thread Pitch (mm)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(inputs, textvariable=self.pitch_var, width=14).grid(row=1, column=1, sticky="w", pady=(8, 0))

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(4, 12))
        ttk.Button(button_row, text="Calculate", command=self.calculate).pack(side="left")
        ttk.Label(button_row, textvariable=self.status_var, foreground="#666666").pack(side="left", padx=(12, 0))

        output = ttk.LabelFrame(frame, text="Results", padding=12)
        output.pack(fill="both", expand=False)

        self._result_row(output, 0, "Theoretical Drill:", self.theoretical_hole_var)
        self._result_row(output, 1, "3D Print Seed Hole:", self.print_hole_var)
        self._result_row(output, 2, "Theoretical Major:", self.theoretical_bolt_var)
        self._result_row(output, 3, "3D Print Cylinder:", self.print_bolt_var)
        self._result_row(output, 4, "Layer Height:", self.layer_var)

        notes = ttk.LabelFrame(frame, text="Guidelines", padding=12)
        notes.pack(fill="both", expand=True, pady=(12, 0))

        note_text = (
            "• Thread tool: Metric Tap for holes, Metric Die for bolts\n"
            "• Method: Cut Thread\n"
            "• Chamfer: 45° lead-in chamfer, at least 1.0 mm\n"
            "• Walls: 4-6 perimeters\n"
            "• Orientation: Print vertically for circularity"
        )
        ttk.Label(notes, text=note_text, justify="left").pack(anchor="w")

    @staticmethod
    def _result_row(parent: ttk.Widget, row: int, label_text: str, value_var: tk.StringVar) -> None:
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Label(parent, textvariable=value_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=row, column=1, sticky="e", padx=(24, 0), pady=2
        )

    def calculate(self) -> None:
        try:
            diameter = float(self.diameter_var.get())
            pitch = float(self.pitch_var.get())
            values = calculate_thread_values(diameter, pitch)
        except ValueError:
            self.status_var.set("Please enter valid positive numbers.")
            return

        self.theoretical_hole_var.set(f"{values.standard_tap_drill:.2f} mm")
        self.print_hole_var.set(f"{values.print_hole:.2f} mm")
        self.theoretical_bolt_var.set(f"{values.theoretical_bolt:.2f} mm")
        self.print_bolt_var.set(f"{values.print_bolt:.2f} mm")
        self.layer_var.set(f"{values.min_layer:.2f} - {values.max_layer:.2f} mm")
        self.status_var.set("Calculated successfully.")


def main() -> None:
    root = tk.Tk()
    app = ThreadCalculatorApp(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()
