"""PySide6 desktop entry point for the 3D printed thread calculator."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QIODevice, QFile, QTimer
from PySide6.QtGui import QAction, QClipboard, QDoubleValidator, QFont, QFontDatabase
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QLineEdit, QMainWindow, QPushButton, QTextEdit, QWidget

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
UI_FILE = Path(__file__).resolve().parent / "ui" / "main_window.ui"


@dataclass(frozen=True)
class DisplayValue:
    title: str
    value: str
    detail: str


@dataclass(frozen=True)
class FieldBinding:
    container: QWidget
    label: QLabel
    input: QLineEdit
    helper: QLabel

    def set_error_state(self, has_error: bool) -> None:
        self.input.setProperty("invalid", has_error)
        self.input.style().unpolish(self.input)
        self.input.style().polish(self.input)


@dataclass(frozen=True)
class ResultRowBinding:
    frame: QFrame
    title_label: QLabel
    value_label: QLabel
    detail_label: QLabel

    def update_value(self, value: DisplayValue) -> None:
        self.title_label.setText(value.title)
        self.value_label.setText(value.value)
        self.detail_label.setText(value.detail)


@dataclass(frozen=True)
class MetricTileBinding:
    frame: QFrame
    title_label: QLabel
    value_label: QLabel


class ThreadCalculatorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.standard = ThreadStandard.METRIC
        self._status_reset_timer = QTimer(self)
        self._status_reset_timer.setSingleShot(True)
        self._status_reset_timer.timeout.connect(self._restore_ready_status)

        self._load_ui()
        self._bind_widgets()
        self._populate_static_data()
        self._apply_fonts()
        self._apply_theme()
        self._build_actions()
        self._connect_signals()
        self._load_defaults_for_standard(self.standard)
        self.recalculate(show_success=False)

    def _load_ui(self) -> None:
        ui_file = QFile(str(UI_FILE))
        if not ui_file.open(QIODevice.ReadOnly):
            raise RuntimeError(f"Unable to open UI file: {UI_FILE}")

        loader = QUiLoader()
        loaded_window = loader.load(ui_file, self)
        ui_file.close()

        if loaded_window is None:
            raise RuntimeError(f"Unable to load UI file: {UI_FILE}")
        if not isinstance(loaded_window, QMainWindow):
            raise RuntimeError(f"UI root must be a QMainWindow: {UI_FILE}")

        self.setWindowTitle(loaded_window.windowTitle())
        self.resize(loaded_window.size())
        self.setMinimumSize(loaded_window.minimumSize())
        self.setCentralWidget(loaded_window.takeCentralWidget())
        self.setStatusBar(loaded_window.statusBar())
        loaded_window.deleteLater()

    def _bind_widgets(self) -> None:
        self.standard_combo = self._require_child(QComboBox, "standardCombo")
        self.preset_combo = self._require_child(QComboBox, "presetCombo")
        self.calculate_button = self._require_child(QPushButton, "calculateButton")
        self.reset_button = self._require_child(QPushButton, "resetButton")
        self.copy_button = self._require_child(QPushButton, "copyButton")
        self.inline_status = self._require_child(QLabel, "inlineStatus")
        self.empty_state_label = self._require_child(QLabel, "emptyState")
        self.notes_box = self._require_child(QTextEdit, "notesBox")

        self.diameter_input = self._bind_field("diameterField", "diameterLabel", "diameterInput", "diameterHelper")
        self.pitch_input = self._bind_field("pitchField", "pitchLabel", "pitchInput", "pitchHelper")

        self.result_rows = {
            "standard_tap_drill": self._bind_result_row("standardTapDrillRow"),
            "print_hole": self._bind_result_row("printHoleRow"),
            "theoretical_bolt": self._bind_result_row("theoreticalBoltRow"),
            "print_bolt": self._bind_result_row("printBoltRow"),
            "layer_range": self._bind_result_row("layerRangeRow"),
        }

        self.summary_standard = self._bind_metric_tile("summaryStandardTile")
        self.summary_input = self._bind_metric_tile("summaryInputTile")
        self.summary_units = self._bind_metric_tile("summaryUnitsTile")
        self.summary_clearance = self._bind_metric_tile("summaryClearanceTile")

        status_bar = self.statusBar()
        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("statusBarLabel")
        status_bar.addWidget(self.status_label, 1)

    def _populate_static_data(self) -> None:
        self._require_child(QLabel, "appTitle").setText(APP_TITLE)
        self._require_child(QLabel, "appSubtitle").setText(APP_SUBTITLE)

        self.standard_combo.clear()
        self.standard_combo.addItems([ThreadStandard.METRIC.value, ThreadStandard.SAE.value])

        self.preset_combo.clear()
        self.preset_combo.addItem("Custom")
        for preset in COMMON_PRESETS:
            self.preset_combo.addItem(preset.name, preset)

        validator = QDoubleValidator(bottom=0.0001, top=9999.0, decimals=6, parent=self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.diameter_input.input.setValidator(validator)
        self.pitch_input.input.setValidator(QDoubleValidator(bottom=0.0001, top=9999.0, decimals=6, parent=self))

    def _require_child(self, widget_type: type[QWidget], name: str) -> QWidget:
        widget = self.findChild(widget_type, name)
        if widget is None:
            raise RuntimeError(f"Missing required widget '{name}' in {UI_FILE}")
        return widget

    def _require_descendant(self, parent: QWidget, widget_type: type[QWidget], name: str) -> QWidget:
        widget = parent.findChild(widget_type, name)
        if widget is None:
            raise RuntimeError(f"Missing required widget '{name}' in {UI_FILE}")
        return widget

    def _bind_field(self, container_name: str, label_name: str, input_name: str, helper_name: str) -> FieldBinding:
        container = self._require_child(QWidget, container_name)
        return FieldBinding(
            container=container,
            label=self._require_descendant(container, QLabel, label_name),
            input=self._require_descendant(container, QLineEdit, input_name),
            helper=self._require_descendant(container, QLabel, helper_name),
        )

    def _bind_result_row(self, frame_name: str) -> ResultRowBinding:
        frame = self._require_child(QFrame, frame_name)
        return ResultRowBinding(
            frame=frame,
            title_label=self._require_descendant(frame, QLabel, "titleLabel"),
            value_label=self._require_descendant(frame, QLabel, "valueLabel"),
            detail_label=self._require_descendant(frame, QLabel, "detailLabel"),
        )

    def _bind_metric_tile(self, frame_name: str) -> MetricTileBinding:
        frame = self._require_child(QFrame, frame_name)
        return MetricTileBinding(
            frame=frame,
            title_label=self._require_descendant(frame, QLabel, "titleLabel"),
            value_label=self._require_descendant(frame, QLabel, "valueLabel"),
        )

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
            QWidget#canvas {{
                background: {BACKGROUND};
            }}
            QMainWindow {{
                background: {BACKGROUND};
            }}
            QFrame#header {{
                background: {PANEL};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
            QFrame#controlsCard, QFrame#notesCard, QFrame#summaryCard, QFrame#detailCard {{
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
                min-height: 46px;
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
                min-height: 44px;
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
            QPushButton#calculateButton {{
                background: {ACCENT};
                color: #08111E;
                border: 1px solid {ACCENT};
            }}
            QPushButton#calculateButton:hover {{
                background: #7AB9FF;
            }}
            QLabel#inlineStatus {{
                border-radius: 12px;
                background: #131A23;
                border: 1px solid {BORDER};
                padding: 12px 14px;
                color: {MUTED};
            }}
            QFrame#standardTapDrillRow, QFrame#printHoleRow, QFrame#theoreticalBoltRow,
            QFrame#printBoltRow, QFrame#layerRangeRow {{
                background: {PANEL_ALT};
                border: 1px solid {BORDER};
                border-radius: 16px;
                min-height: 118px;
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
            QFrame#summaryStandardTile, QFrame#summaryInputTile, QFrame#summaryUnitsTile, QFrame#summaryClearanceTile {{
                background: {PANEL_ALT};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            QLabel#metricTileValue {{
                font-size: 18px;
                font-weight: 700;
            }}
            QTextEdit#notesBox {{
                min-height: 260px;
                padding: 12px;
                line-height: 1.45;
            }}
            QScrollArea {{
                border: none;
            }}
            QScrollBar:vertical {{
                background: {PANEL};
                width: 12px;
                margin: 6px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: #334156;
                min-height: 36px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
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
