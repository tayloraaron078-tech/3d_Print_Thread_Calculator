"""PySide6 desktop entry point for the 3D printed thread calculator."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QClipboard, QDoubleValidator, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from thread_logic import COMMON_PRESETS, ThreadCalculation, ThreadInput, ThreadStandard, calculate_thread_values, parse_thread_inputs

APP_TITLE = "Redeemed Thread Calculator"
APP_SUBTITLE = "Premium-fit sizing guidance for 3D printed metric and unified threads."
ACCENT = "#5AA9FF"
BACKGROUND = "#10141C"
PANEL = "#171C26"
PANEL_ALT = "#1D2430"
BORDER = "#2A3444"
TEXT = "#EAF1FF"
MUTED = "#9BA9C0"
SUCCESS = "#5FD1A3"
WARNING = "#FFBF69"
ERROR = "#FF7B88"


@dataclass(frozen=True)
class DisplayValue:
    title: str
    value: str
    detail: str


class CardFrame(QFrame):
    def __init__(self, title: str = "", description: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        if title:
            header = QVBoxLayout()
            header.setSpacing(4)

            title_label = QLabel(title)
            title_label.setObjectName("cardTitle")
            header.addWidget(title_label)

            if description:
                description_label = QLabel(description)
                description_label.setObjectName("cardDescription")
                description_label.setWordWrap(True)
                header.addWidget(description_label)

            layout.addLayout(header)

        self.content_layout = layout


class LabeledInput(QWidget):
    def __init__(self, label_text: str, helper_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.label = QLabel(label_text)
        self.label.setObjectName("fieldLabel")
        self.helper = QLabel(helper_text)
        self.helper.setObjectName("fieldHelper")
        self.helper.setWordWrap(True)
        self.input = QLineEdit()
        self.input.setClearButtonEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.addWidget(self.helper)

    def set_error_state(self, has_error: bool) -> None:
        self.input.setProperty("invalid", has_error)
        self.input.style().unpolish(self.input)
        self.input.style().polish(self.input)


class ResultRow(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultRow")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("resultTitle")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("resultValue")
        self.value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail_label = QLabel("Awaiting valid inputs")
        self.detail_label.setObjectName("resultDetail")
        self.detail_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(2)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def update_value(self, value: DisplayValue) -> None:
        self.title_label.setText(value.title)
        self.value_label.setText(value.value)
        self.detail_label.setText(value.detail)


class ThreadCalculatorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        self.setMinimumSize(1024, 680)

        self.standard = ThreadStandard.METRIC
        self._status_reset_timer = QTimer(self)
        self._status_reset_timer.setSingleShot(True)
        self._status_reset_timer.timeout.connect(self._restore_ready_status)

        self._build_ui()
        self._apply_fonts()
        self._apply_theme()
        self._connect_signals()
        self._load_defaults_for_standard(self.standard)
        self.recalculate(show_success=False)

    def _build_ui(self) -> None:
        container = QWidget()
        outer_layout = QVBoxLayout(container)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(18)

        outer_layout.addWidget(self._build_header())

        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)
        content_layout.addWidget(self._build_left_column(), 5)
        content_layout.addWidget(self._build_right_column(), 6)
        outer_layout.addLayout(content_layout, 1)

        self.setCentralWidget(container)
        self.setStatusBar(self._build_status_bar())
        self._build_actions()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(6)

        title = QLabel(APP_TITLE)
        title.setObjectName("appTitle")
        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        return header

    def _build_left_column(self) -> QWidget:
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        controls_card = CardFrame("Inputs & controls", "Choose a standard, enter the nominal size, and the calculator updates instantly.")
        controls_grid = QGridLayout()
        controls_grid.setHorizontalSpacing(12)
        controls_grid.setVerticalSpacing(16)

        standard_box = QWidget()
        standard_layout = QVBoxLayout(standard_box)
        standard_layout.setContentsMargins(0, 0, 0, 0)
        standard_layout.setSpacing(6)
        standard_label = QLabel("Thread standard")
        standard_label.setObjectName("fieldLabel")
        self.standard_combo = QComboBox()
        self.standard_combo.addItems([ThreadStandard.METRIC.value, ThreadStandard.SAE.value])
        standard_helper = QLabel("Metric uses diameter + pitch. SAE uses diameter + threads per inch.")
        standard_helper.setObjectName("fieldHelper")
        standard_helper.setWordWrap(True)
        standard_layout.addWidget(standard_label)
        standard_layout.addWidget(self.standard_combo)
        standard_layout.addWidget(standard_helper)

        preset_box = QWidget()
        preset_layout = QVBoxLayout(preset_box)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(6)
        preset_label = QLabel("Quick presets")
        preset_label.setObjectName("fieldLabel")
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Custom")
        for preset in COMMON_PRESETS:
            self.preset_combo.addItem(preset.name, preset)
        preset_helper = QLabel("Apply a common starting point, then fine-tune if needed.")
        preset_helper.setObjectName("fieldHelper")
        preset_helper.setWordWrap(True)
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(preset_helper)

        self.diameter_input = LabeledInput("Nominal diameter (mm)", "Positive numeric value for the fastener major diameter.")
        self.pitch_input = LabeledInput("Thread pitch (mm)", "Distance between threads for metric, or TPI for unified threads.")

        validator = QDoubleValidator(bottom=0.0001, top=9999.0, decimals=6)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.diameter_input.input.setValidator(validator)
        self.pitch_input.input.setValidator(QDoubleValidator(bottom=0.0001, top=9999.0, decimals=6))

        controls_grid.addWidget(standard_box, 0, 0)
        controls_grid.addWidget(preset_box, 0, 1)
        controls_grid.addWidget(self.diameter_input, 1, 0)
        controls_grid.addWidget(self.pitch_input, 1, 1)
        controls_grid.setColumnStretch(0, 1)
        controls_grid.setColumnStretch(1, 1)

        controls_card.content_layout.addLayout(controls_grid)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.setObjectName("accentButton")
        self.reset_button = QPushButton("Reset")
        self.copy_button = QPushButton("Copy results")
        button_row.addWidget(self.calculate_button)
        button_row.addWidget(self.reset_button)
        button_row.addWidget(self.copy_button)
        button_row.addStretch(1)
        controls_card.content_layout.addLayout(button_row)

        self.inline_status = QLabel("Ready for input.")
        self.inline_status.setObjectName("inlineStatus")
        self.inline_status.setWordWrap(True)
        controls_card.content_layout.addWidget(self.inline_status)

        notes_card = CardFrame("Engineering notes", "These settings are intended as reliable starting dimensions for FDM/CAD workflows.")
        notes = QTextEdit()
        notes.setObjectName("notesBox")
        notes.setReadOnly(True)
        notes.setText(
            "• Thread tool: use a metric tap for internal threads and a die profile for external threads.\n"
            "• Method: cut thread geometry rather than cosmetic representations.\n"
            "• Chamfer: add a 45° lead-in, ideally at least 1.0 mm long.\n"
            "• Walls: target 4–6 perimeters for strength and clean thread form.\n"
            "• Orientation: print vertically when possible to maintain circularity.\n"
            "• The calculator values are optimized as practical starting points for test fits.\n"
            "• Originally tuned around SolidWorks-style modeling, but portable to other CAD packages."
        )
        notes_card.content_layout.addWidget(notes)

        layout.addWidget(controls_card)
        layout.addWidget(notes_card, 1)
        return column

    def _build_right_column(self) -> QWidget:
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        summary_card = CardFrame("Calculated results", "All outputs update automatically and are formatted for direct use in CAD or slicer setup.")
        self.result_rows = {
            "standard_tap_drill": ResultRow("Recommended tap drill"),
            "print_hole": ResultRow("3D print hole diameter"),
            "theoretical_bolt": ResultRow("Theoretical bolt major diameter"),
            "print_bolt": ResultRow("Recommended print bolt diameter"),
            "layer_range": ResultRow("Suggested layer height range"),
        }
        for row in self.result_rows.values():
            summary_card.content_layout.addWidget(row)

        empty_state = QLabel("Enter dimensions on the left to generate production-ready thread sizing guidance.")
        empty_state.setObjectName("emptyState")
        empty_state.setWordWrap(True)
        summary_card.content_layout.addWidget(empty_state)
        self.empty_state_label = empty_state

        detail_card = CardFrame("Fit guidance", "Use the highlighted values as a baseline, then fine-tune for your material, printer, and tolerance preference.")
        detail_grid = QGridLayout()
        detail_grid.setHorizontalSpacing(16)
        detail_grid.setVerticalSpacing(16)

        self.summary_standard = self._build_metric_tile("Current standard", "Metric")
        self.summary_input = self._build_metric_tile("Input size", "M8 × 1.25")
        self.summary_units = self._build_metric_tile("Output units", "mm")
        self.summary_clearance = self._build_metric_tile("Thread fit note", "Balanced")

        tiles = [self.summary_standard, self.summary_input, self.summary_units, self.summary_clearance]
        for index, tile in enumerate(tiles):
            detail_grid.addWidget(tile, index // 2, index % 2)

        detail_card.content_layout.addLayout(detail_grid)

        layout.addWidget(summary_card, 3)
        layout.addWidget(detail_card, 2)
        return column

    def _build_metric_tile(self, title: str, value: str) -> QFrame:
        tile = QFrame()
        tile.setObjectName("metricTile")
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(16, 16, 16, 16)
        tile_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("metricTileTitle")
        value_label = QLabel(value)
        value_label.setObjectName("metricTileValue")

        tile_layout.addWidget(title_label)
        tile_layout.addWidget(value_label)
        tile.value_label = value_label  # type: ignore[attr-defined]
        return tile

    def _build_status_bar(self) -> QStatusBar:
        status_bar = QStatusBar()
        status_bar.setSizeGripEnabled(False)
        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("statusBarLabel")
        status_bar.addWidget(self.status_label, 1)
        return status_bar

    def _build_actions(self) -> None:
        copy_action = QAction("Copy Results", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_results)
        self.addAction(copy_action)

        reset_action = QAction("Reset Inputs", self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.triggered.connect(self.reset_inputs)
        self.addAction(reset_action)

    def _apply_fonts(self) -> None:
        families = {family.lower(): family for family in QFontDatabase.families()}
        preferred = next((families[name] for name in ("inter", "segoe ui", "sf pro text", "noto sans") if name in families), None)
        if preferred:
            QApplication.instance().setFont(QFont(preferred, 10))

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {BACKGROUND};
                color: {TEXT};
            }}
            QMainWindow {{
                background: {BACKGROUND};
            }}
            QFrame#header {{
                background: {PANEL};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
            QFrame#card {{
                background: {PANEL};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            QLabel#appTitle {{
                font-size: 28px;
                font-weight: 700;
                letter-spacing: 0.3px;
            }}
            QLabel#appSubtitle, QLabel#cardDescription, QLabel#fieldHelper, QLabel#resultDetail,
            QLabel#metricTileTitle, QLabel#statusBarLabel {{
                color: {MUTED};
            }}
            QLabel#cardTitle {{
                font-size: 16px;
                font-weight: 700;
            }}
            QLabel#fieldLabel {{
                font-size: 12px;
                font-weight: 600;
            }}
            QLineEdit, QComboBox, QTextEdit {{
                background: {PANEL_ALT};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 10px 12px;
                selection-background-color: {ACCENT};
                selection-color: #09111E;
            }}
            QLineEdit:hover, QComboBox:hover, QTextEdit:hover {{
                border-color: #3A4A61;
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 1px solid {ACCENT};
            }}
            QLineEdit[invalid="true"] {{
                border: 1px solid {ERROR};
                background: #23171D;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0;
                height: 0;
            }}
            QPushButton {{
                background: {PANEL_ALT};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: #4A5D77;
                background: #232D3A;
            }}
            QPushButton:pressed {{
                background: #1A222D;
            }}
            QPushButton#accentButton {{
                background: {ACCENT};
                color: #08111E;
                border: 1px solid {ACCENT};
            }}
            QPushButton#accentButton:hover {{
                background: #7AB9FF;
            }}
            QLabel#inlineStatus {{
                border-radius: 12px;
                background: #131A23;
                border: 1px solid {BORDER};
                padding: 12px 14px;
                color: {MUTED};
            }}
            QFrame#resultRow {{
                background: {PANEL_ALT};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            QLabel#resultTitle {{
                font-size: 12px;
                font-weight: 600;
                color: {MUTED};
            }}
            QLabel#resultValue {{
                font-size: 24px;
                font-weight: 700;
                color: {TEXT};
            }}
            QLabel#emptyState {{
                color: {MUTED};
                padding-top: 6px;
            }}
            QFrame#metricTile {{
                background: {PANEL_ALT};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            QLabel#metricTileValue {{
                font-size: 18px;
                font-weight: 700;
            }}
            QTextEdit#notesBox {{
                min-height: 210px;
                padding: 12px;
                line-height: 1.45;
            }}
            QStatusBar {{
                background: {PANEL};
                border-top: 1px solid {BORDER};
            }}
            QStatusBar::item {{
                border: none;
            }}
            """
        )

    def _connect_signals(self) -> None:
        self.standard_combo.currentTextChanged.connect(self._on_standard_changed)
        self.preset_combo.currentIndexChanged.connect(self._apply_selected_preset)
        self.calculate_button.clicked.connect(self.recalculate)
        self.reset_button.clicked.connect(self.reset_inputs)
        self.copy_button.clicked.connect(self.copy_results)
        self.diameter_input.input.textChanged.connect(self._handle_input_change)
        self.pitch_input.input.textChanged.connect(self._handle_input_change)

    def _on_standard_changed(self, value: str) -> None:
        self.standard = ThreadStandard(value)
        self._sync_labels()
        self._load_defaults_for_standard(self.standard)
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)
        self.recalculate(show_success=False)

    def _apply_selected_preset(self, index: int) -> None:
        if index <= 0:
            return

        preset = self.preset_combo.currentData()
        if preset is None:
            return

        self.standard_combo.setCurrentText(preset.standard.value)
        self.diameter_input.input.setText(f"{preset.diameter:g}")
        self.pitch_input.input.setText(f"{preset.pitch_or_tpi:g}")
        self.recalculate(show_success=True, message=f"Applied preset: {preset.name}.")

    def _load_defaults_for_standard(self, standard: ThreadStandard) -> None:
        if standard == ThreadStandard.METRIC:
            diameter, pitch = "8", "1.25"
        else:
            diameter, pitch = "0.25", "20"
        self.diameter_input.input.setText(diameter)
        self.pitch_input.input.setText(pitch)
        self._sync_labels()

    def _sync_labels(self) -> None:
        is_metric = self.standard == ThreadStandard.METRIC
        self.diameter_input.label.setText(f"Nominal diameter ({'mm' if is_metric else 'in'})")
        self.pitch_input.label.setText("Thread pitch (mm)" if is_metric else "Threads per inch (TPI)")
        self.pitch_input.helper.setText(
            "Distance between adjacent threads in millimeters."
            if is_metric
            else "Threads per inch are converted to pitch internally for the calculations."
        )

    def _handle_input_change(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)
        self.recalculate(show_success=False)

    def _read_inputs(self) -> ThreadInput:
        diameter_text = self.diameter_input.input.text().strip()
        pitch_text = self.pitch_input.input.text().strip()

        has_error = False
        try:
            diameter = float(diameter_text)
        except ValueError as exc:
            has_error = True
            diameter = 0.0
            diameter_error = exc
        else:
            diameter_error = None

        try:
            pitch_or_tpi = float(pitch_text)
        except ValueError as exc:
            has_error = True
            pitch_or_tpi = 0.0
            pitch_error = exc
        else:
            pitch_error = None

        self.diameter_input.set_error_state(diameter_error is not None or diameter <= 0)
        self.pitch_input.set_error_state(pitch_error is not None or pitch_or_tpi <= 0)

        if has_error or diameter <= 0 or pitch_or_tpi <= 0:
            raise ValueError("Enter positive numeric values for both inputs.")

        return parse_thread_inputs(self.standard, diameter, pitch_or_tpi)

    def recalculate(self, show_success: bool = True, message: str | None = None) -> None:
        try:
            parsed = self._read_inputs()
            values = calculate_thread_values(parsed.diameter, parsed.pitch)
        except ValueError as error:
            self._set_empty_state(True)
            self._set_results_placeholder()
            self._set_status(str(error), state="error")
            return

        self._update_results(parsed, values)
        self._set_empty_state(False)
        if show_success:
            self._set_status(message or "Calculated successfully.", state="success", auto_reset=True)
        else:
            self._set_status("Results updated automatically.", state="neutral")

    def _update_results(self, parsed: ThreadInput, values: ThreadCalculation) -> None:
        unit = parsed.units
        scale = parsed.display_scale

        displays = {
            "standard_tap_drill": DisplayValue(
                "Recommended tap drill",
                f"{values.standard_tap_drill * scale:.3f} {unit}",
                "Baseline drill size before adding print-specific clearance.",
            ),
            "print_hole": DisplayValue(
                "Recommended printed hole diameter",
                f"{values.print_hole * scale:.3f} {unit}",
                "Includes extra clearance to improve printed thread engagement.",
            ),
            "theoretical_bolt": DisplayValue(
                "Theoretical bolt major diameter",
                f"{values.theoretical_bolt * scale:.3f} {unit}",
                "Nominal size before print compensation is applied.",
            ),
            "print_bolt": DisplayValue(
                "Recommended printed bolt diameter",
                f"{values.print_bolt * scale:.3f} {unit}",
                "Reduced slightly to account for real-world material buildup.",
            ),
            "layer_range": DisplayValue(
                "Suggested layer height range",
                f"{values.min_layer * scale:.3f} – {values.max_layer * scale:.3f} {unit}",
                "Staying in this range helps preserve thread detail and fit.",
            ),
        }

        for key, display in displays.items():
            self.result_rows[key].update_value(display)

        input_size = (
            f"M{self.diameter_input.input.text().strip()} × {self.pitch_input.input.text().strip()}"
            if self.standard == ThreadStandard.METRIC
            else f"{self.diameter_input.input.text().strip()}-{self.pitch_input.input.text().strip()}"
        )
        clearance_note = "Fine pitch / tighter clearance" if parsed.pitch < 1.5 else "Coarser pitch / added clearance"

        self.summary_standard.value_label.setText(self.standard.value)
        self.summary_input.value_label.setText(input_size)
        self.summary_units.value_label.setText(unit)
        self.summary_clearance.value_label.setText(clearance_note)

    def _set_results_placeholder(self) -> None:
        placeholder = DisplayValue("Awaiting valid input", "—", "Enter a positive value to calculate.")
        for row in self.result_rows.values():
            row.update_value(placeholder)
        self.summary_clearance.value_label.setText("Validation needed")

    def _set_empty_state(self, visible: bool) -> None:
        self.empty_state_label.setVisible(visible)

    def _set_status(self, message: str, state: str = "neutral", auto_reset: bool = False) -> None:
        palette = {
            "neutral": (MUTED, BORDER, "#131A23"),
            "success": (SUCCESS, SUCCESS, "#10241D"),
            "warning": (WARNING, WARNING, "#2A2112"),
            "error": (ERROR, ERROR, "#2A171B"),
        }
        text_color, border_color, background = palette[state]
        self.inline_status.setText(message)
        self.inline_status.setStyleSheet(
            f"color: {text_color}; border: 1px solid {border_color}; background: {background}; padding: 12px 14px; border-radius: 12px;"
        )
        self.status_label.setText(message)
        if auto_reset:
            self._status_reset_timer.start(3000)

    def _restore_ready_status(self) -> None:
        self._set_status("Ready for input.", state="neutral")

    def reset_inputs(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)
        self._load_defaults_for_standard(self.standard)
        self.recalculate(show_success=True, message="Inputs reset to default values.")

    def copy_results(self) -> None:
        try:
            parsed = self._read_inputs()
            values = calculate_thread_values(parsed.diameter, parsed.pitch)
        except ValueError:
            self._set_status("Cannot copy results until the inputs are valid.", state="warning", auto_reset=True)
            return

        scale = parsed.display_scale
        unit = parsed.units
        summary = (
            f"{APP_TITLE}\n"
            f"Standard: {self.standard.value}\n"
            f"Input: diameter={self.diameter_input.input.text().strip()}, second value={self.pitch_input.input.text().strip()}\n"
            f"Tap drill: {values.standard_tap_drill * scale:.3f} {unit}\n"
            f"Printed hole: {values.print_hole * scale:.3f} {unit}\n"
            f"Theoretical bolt diameter: {values.theoretical_bolt * scale:.3f} {unit}\n"
            f"Printed bolt diameter: {values.print_bolt * scale:.3f} {unit}\n"
            f"Layer height range: {values.min_layer * scale:.3f} - {values.max_layer * scale:.3f} {unit}"
        )
        QApplication.clipboard().setText(summary, QClipboard.Clipboard)
        self._set_status("Results copied to clipboard.", state="success", auto_reset=True)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("Redeemed Engineering")
    window = ThreadCalculatorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
