from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cfclient.ui.flightrl.health_widget import HealthWidget
from cfclient.ui.flightrl.log_model import DECISION_KEYS, FlightRLLog, FlightRLRow, load_log
from cfclient.ui.flightrl.ranger_widget import RangerBubbleWidget
from cfclient.ui.flightrl.timeline_widget import DecisionTimelineWidget
from cfclient.ui.tab_toolbox import TabToolbox

DEFAULT_LOG_DIR = Path("/Users/sebastianboehler/Documents/GitHub/FlightRL/artifacts/crazyflie_logs")


class FlightRLInspectorTab(TabToolbox):
    def __init__(self, helper):
        super().__init__(helper, "FlightRL Inspector")
        self._log: FlightRLLog | None = None
        self._build_ui()
        self._refresh_files()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.path_edit = QLineEdit(str(DEFAULT_LOG_DIR if DEFAULT_LOG_DIR.exists() else Path.cwd()))
        browse = QPushButton("Browse")
        refresh = QPushButton("Refresh")
        browse.clicked.connect(self._browse)
        refresh.clicked.connect(self._refresh_files)
        toolbar.addWidget(QLabel("Logs"))
        toolbar.addWidget(self.path_edit, 1)
        toolbar.addWidget(browse)
        toolbar.addWidget(refresh)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([300, 820])
        root.addWidget(splitter, 1)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.file_list = QListWidget()
        self.file_list.currentItemChanged.connect(self._load_selected)
        self.summary_table = self._new_table()
        layout.addWidget(self.file_list, 2)
        layout.addWidget(QLabel("Summary"))
        layout.addWidget(self.summary_table, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        row_bar = QHBoxLayout()
        self.row_label = QLabel("Row 0 / 0")
        self.row_slider = QSlider(Qt.Orientation.Horizontal)
        self.row_slider.setEnabled(False)
        self.row_slider.valueChanged.connect(self._row_changed)
        row_bar.addWidget(self.row_label)
        row_bar.addWidget(self.row_slider, 1)
        layout.addLayout(row_bar)

        self.ranger = RangerBubbleWidget()
        self.timeline = DecisionTimelineWidget()
        self.health = HealthWidget()
        self.row_table = self._new_table()
        layout.addWidget(self.ranger, 2)
        layout.addWidget(self.timeline)
        layout.addWidget(self.health)
        layout.addWidget(QLabel("Selected Row"))
        layout.addWidget(self.row_table, 2)
        return panel

    def _new_table(self) -> QTableWidget:
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(("Field", "Value"))
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        return table

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "FlightRL logs", self.path_edit.text())
        if path:
            self.path_edit.setText(path)
            self._refresh_files()

    def _refresh_files(self) -> None:
        self.file_list.clear()
        directory = Path(self.path_edit.text()).expanduser()
        if not directory.exists():
            self._set_summary([("Status", "directory not found")])
            return
        files = sorted(directory.glob("*.csv"), key=lambda item: item.stat().st_mtime, reverse=True)
        for path in files:
            self.file_list.addItem(path.name)
        self.file_list.setProperty("directory", str(directory))
        self._set_summary([("CSV files", str(len(files))), ("Directory", str(directory))])

    def _load_selected(self, current, previous) -> None:
        if current is None:
            return
        directory = Path(self.file_list.property("directory") or self.path_edit.text())
        path = directory / current.text()
        try:
            self._log = load_log(path)
        except Exception as exc:
            QMessageBox.warning(self, "FlightRL Inspector", f"Could not load log:\n{exc}")
            return
        last = max(0, len(self._log.rows) - 1)
        self.timeline.set_log(self._log)
        self.row_slider.blockSignals(True)
        self.row_slider.setEnabled(bool(self._log.rows))
        self.row_slider.setMaximum(last)
        self.row_slider.setValue(0)
        self.row_slider.blockSignals(False)
        self._set_summary(self._summary_rows(self._log))
        self._show_row(0)

    def _row_changed(self, value: int) -> None:
        self._show_row(value)

    def _show_row(self, index: int) -> None:
        row = self._row(index)
        count = len(self._log.rows) if self._log else 0
        self.row_label.setText(f"Row {index + 1 if row else 0} / {count}")
        self.ranger.set_row(row)
        self.timeline.set_row_index(index)
        self.health.set_state(self._log, row)
        self._set_row_table(row)

    def _row(self, index: int) -> FlightRLRow | None:
        if self._log is None or not self._log.rows:
            return None
        return self._log.rows[max(0, min(index, len(self._log.rows) - 1))]

    def _summary_rows(self, log: FlightRLLog) -> list[tuple[str, str]]:
        summary = log.summary
        rows = [
            ("File", log.path.name),
            ("Rows", str(summary.row_count)),
            ("Duration", f"{summary.duration_s:.2f}s"),
            ("Columns", str(summary.columns)),
            ("Field groups", ", ".join(summary.field_groups) or "none"),
            ("Min range", self._fmt(summary.min_horizontal_range_m, "m")),
            ("Max state speed", self._fmt(summary.max_horizontal_speed_m_s, "m/s")),
            ("Max command speed", self._fmt(summary.max_command_speed_m_s, "m/s")),
            ("Battery min/latest", f"{self._fmt(summary.battery_min_v, 'V')} / {self._fmt(summary.battery_latest_v, 'V')}"),
        ]
        rows.extend((key.replace("_", " "), f"{value * 100:.1f}%") for key, value in summary.active_fractions.items())
        if summary.health_warnings:
            rows.append(("Health", ", ".join(summary.health_warnings)))
        return rows

    def _set_row_table(self, row: FlightRLRow | None) -> None:
        if row is None:
            self._set_table(self.row_table, [])
            return
        keys = [
            "host_time_s",
            "stateEstimate.x", "stateEstimate.y", "stateEstimate.z",
            "stateEstimate.vx", "stateEstimate.vy", "stateEstimate.vz",
            "range.front", "range.back", "range.left", "range.right", "range.up", "range.zrange",
            "vx_m_s", "vy_m_s", "vz_m_s", "yawrate_deg_s",
            "raw_vx_m_s", "raw_vy_m_s", "puffer_vx_m_s", "puffer_vy_m_s",
            "action_thrust", "action_roll_rate", "action_pitch_rate", "action_yaw_rate",
            "thrust_percent", "commander_pitch_rate_deg_s", "pm.vbat", "radio.rssi",
            *DECISION_KEYS,
        ]
        rows = [(key, row.values.get(key, "")) for key in keys if key in row.values]
        self._set_table(self.row_table, rows)

    def _set_summary(self, rows: list[tuple[str, str]]) -> None:
        self._set_table(self.summary_table, rows)

    def _set_table(self, table: QTableWidget, rows: list[tuple[str, str]]) -> None:
        table.setRowCount(len(rows))
        for row_index, (key, value) in enumerate(rows):
            table.setItem(row_index, 0, QTableWidgetItem(key))
            table.setItem(row_index, 1, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

    def _fmt(self, value: float | None, suffix: str) -> str:
        return "n/a" if value is None else f"{value:.3f}{suffix}"
