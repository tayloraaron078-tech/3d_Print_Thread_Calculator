"""Core thread calculation logic for metric and SAE 3D printed threads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ThreadStandard(str, Enum):
    METRIC = "Metric"
    SAE = "SAE"


@dataclass(frozen=True)
class ThreadCalculation:
    standard_tap_drill: float
    print_hole: float
    theoretical_bolt: float
    print_bolt: float
    min_layer: float
    max_layer: float


@dataclass(frozen=True)
class ThreadInput:
    diameter: float
    pitch: float
    units: str
    display_scale: float


@dataclass(frozen=True)
class Preset:
    name: str
    standard: ThreadStandard
    diameter: float
    pitch_or_tpi: float


COMMON_PRESETS: tuple[Preset, ...] = (
    Preset("M5 × 0.8", ThreadStandard.METRIC, 5.0, 0.8),
    Preset("M6 × 1.0", ThreadStandard.METRIC, 6.0, 1.0),
    Preset("M8 × 1.25", ThreadStandard.METRIC, 8.0, 1.25),
    Preset('1/4-20 UNC', ThreadStandard.SAE, 0.25, 20.0),
    Preset('3/8-16 UNC', ThreadStandard.SAE, 0.375, 16.0),
)


def parse_thread_inputs(standard: str, diameter: float, pitch_or_tpi: float) -> ThreadInput:
    """Parse and normalize user inputs for either metric or SAE threads."""
    if diameter <= 0 or pitch_or_tpi <= 0:
        raise ValueError("Diameter and pitch/TPI must both be positive numbers.")

    normalized_standard = standard.strip().lower()
    if normalized_standard == ThreadStandard.METRIC.value.lower():
        return ThreadInput(diameter=diameter, pitch=pitch_or_tpi, units="mm", display_scale=1.0)

    if normalized_standard == ThreadStandard.SAE.value.lower():
        return ThreadInput(
            diameter=diameter * 25.4,
            pitch=(1.0 / pitch_or_tpi) * 25.4,
            units="in",
            display_scale=1.0 / 25.4,
        )

    raise ValueError("Thread standard must be Metric or SAE.")



def calculate_thread_values(diameter: float, pitch: float) -> ThreadCalculation:
    """Calculate thread dimensions using the original calculator logic."""
    if diameter <= 0 or pitch <= 0:
        raise ValueError("Diameter and pitch must both be positive numbers.")

    theoretical_minor = diameter - (1.082532 * pitch)
    hole_clearance = 0.2 if pitch < 1.5 else 0.3
    bolt_clearance = 0.2 if pitch < 1.5 else 0.35

    standard_tap_drill = theoretical_minor + (pitch * 0.12)
    print_hole = standard_tap_drill + hole_clearance
    print_bolt = diameter - bolt_clearance
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
