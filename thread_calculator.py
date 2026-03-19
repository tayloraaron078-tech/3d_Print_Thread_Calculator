"""3D print thread calculator for metric and SAE threads.

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


@dataclass
class ThreadInput:
    diameter: float
    pitch: float
    units: str
    display_scale: float


def parse_thread_inputs(standard: str, diameter: float, pitch_or_tpi: float) -> ThreadInput:
    """Parse and normalize user inputs for either metric or SAE threads.

    For metric threads, the second value is thread pitch.
    For SAE threads, the second value is threads-per-inch (TPI), converted to pitch.
    """
    if diameter <= 0 or pitch_or_tpi <= 0:
        raise ValueError("Diameter and pitch/TPI must both be positive numbers.")

    normalized_standard = standard.lower()
    if normalized_standard == "metric":
        return ThreadInput(diameter=diameter, pitch=pitch_or_tpi, units="mm", display_scale=1.0)
    if normalized_standard == "sae":
        return ThreadInput(
            diameter=diameter * 25.4,
            pitch=(1.0 / pitch_or_tpi) * 25.4,
            units="in",
            display_scale=1.0 / 25.4,
        )

    raise ValueError("Thread standard must be Metric or SAE.")


def calculate_thread_values(diameter: float, pitch: float) -> ThreadCalculation:
    """Calculate thread dimensions using the provided logic.

    Args:
        diameter: Nominal diameter (D).
        pitch: Thread pitch (P).

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
        self.root.title("Redeemed_3D Printed Threads Calculator")
        self.root.geometry("760x560")
        self.root.resizable(False, False)

        self.standard_var = tk.StringVar(value="Metric")
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

        title = ttk.Label(frame, text="Redeemed_3D Printed Threads Calculator", font=("TkDefaultFont", 14, "bold"))
        title.pack(anchor="w", pady=(0, 12))

        inputs = ttk.Frame(frame)
        inputs.pack(fill="x", pady=(0, 10))

        ttk.Label(inputs, text="Thread Standard").grid(row=0, column=0, sticky="w", padx=(0, 8))
        standard_dropdown = ttk.Combobox(
            inputs,
            textvariable=self.standard_var,
            values=["Metric", "SAE"],
            state="readonly",
            width=12,
        )
        standard_dropdown.grid(row=0, column=1, sticky="w")
        standard_dropdown.bind("<<ComboboxSelected>>", self._on_standard_change)

        self.diameter_label = ttk.Label(inputs, text="Nominal Diameter (mm)")
        self.diameter_label.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(inputs, textvariable=self.diameter_var, width=14).grid(row=1, column=1, sticky="w", pady=(8, 0))

        self.pitch_label = ttk.Label(inputs, text="Thread Pitch (mm)")
        self.pitch_label.grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(inputs, textvariable=self.pitch_var, width=14).grid(row=2, column=1, sticky="w", pady=(8, 0))

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

    def _on_standard_change(self, _event: tk.Event) -> None:
        if self.standard_var.get() == "Metric":
            self.diameter_label.configure(text="Nominal Diameter (mm)")
            self.pitch_label.configure(text="Thread Pitch (mm)")
            self.diameter_var.set("8")
            self.pitch_var.set("1.25")
        else:
            self.diameter_label.configure(text="Nominal Diameter (in)")
            self.pitch_label.configure(text="Threads Per Inch (TPI)")
            self.diameter_var.set("0.25")
            self.pitch_var.set("20")
        self.calculate()

    @staticmethod
    def _result_row(parent: ttk.Widget, row: int, label_text: str, value_var: tk.StringVar) -> None:
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Label(parent, textvariable=value_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=row, column=1, sticky="e", padx=(24, 0), pady=2
        )

    def calculate(self) -> None:
        try:
            parsed = parse_thread_inputs(
                self.standard_var.get(),
                float(self.diameter_var.get()),
                float(self.pitch_var.get()),
            )
            values = calculate_thread_values(parsed.diameter, parsed.pitch)
        except ValueError:
            self.status_var.set("Please enter valid positive numbers.")
            return

        self.theoretical_hole_var.set(f"{values.standard_tap_drill * parsed.display_scale:.3f} {parsed.units}")
        self.print_hole_var.set(f"{values.print_hole * parsed.display_scale:.3f} {parsed.units}")
        self.theoretical_bolt_var.set(f"{values.theoretical_bolt * parsed.display_scale:.3f} {parsed.units}")
        self.print_bolt_var.set(f"{values.print_bolt * parsed.display_scale:.3f} {parsed.units}")
        self.layer_var.set(
            f"{values.min_layer * parsed.display_scale:.3f} - {values.max_layer * parsed.display_scale:.3f} {parsed.units}"
        )
        self.status_var.set("Calculated successfully.")


def main() -> None:
    root = tk.Tk()
    app = ThreadCalculatorApp(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()
