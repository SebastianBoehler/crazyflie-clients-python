from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from cfclient.ui.flightrl.log_model import FlightRLLog, FlightRLRow


class HealthWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._log: FlightRLLog | None = None
        self._row: FlightRLRow | None = None
        self.setMinimumHeight(150)

    def set_state(self, log: FlightRLLog | None, row: FlightRLRow | None) -> None:
        self._log = log
        self._row = row
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        self._draw_frame(painter)
        if self._row is None:
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No selected row")
            return
        items = self._items()
        x = 14
        y = 42
        for label, value, color in items:
            self._draw_pill(painter, QRectF(x, y, 148, 28), label, value, color)
            x += 160
            if x + 150 > self.width():
                x = 14
                y += 38

    def _draw_frame(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#dde1e6"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.setPen(QColor("#5c6370"))
        painter.drawText(12, 22, "Health & Link")

    def _items(self) -> list[tuple[str, str, QColor]]:
        row = self._row
        battery = row.number("pm.vbat")
        rssi = row.number("radio.rssi")
        return [
            ("Battery", self._fmt(battery, "V"), self._battery_color(battery)),
            ("Battery %", self._fmt(row.number("pm.batteryLevel"), "%"), QColor("#3b7dd8")),
            ("RSSI", self._fmt(rssi, ""), self._rssi_color(rssi)),
            ("Connected", self._yes_no(row, "radio.isConnected"), self._flag_color(row, "radio.isConnected", True)),
            ("Can fly", self._yes_no(row, "sys.canfly"), self._flag_color(row, "sys.canfly", True)),
            ("Flying", self._yes_no(row, "sys.isFlying"), QColor("#3b7dd8")),
            ("Tumbled", self._yes_no(row, "sys.isTumbled"), self._flag_color(row, "sys.isTumbled", False)),
            ("Motor", self._yes_no(row, "health.motorPass"), self._flag_color(row, "health.motorPass", True)),
            ("Battery health", self._yes_no(row, "health.batteryPass"), self._flag_color(row, "health.batteryPass", True)),
        ]

    def _draw_pill(self, painter: QPainter, rect: QRectF, label: str, value: str, color: QColor) -> None:
        painter.setPen(QPen(color.darker(120), 1))
        painter.setBrush(color.lighter(178))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(QColor("#5c6370"))
        painter.drawText(rect.adjusted(8, 2, -8, -12), Qt.AlignmentFlag.AlignLeft, label)
        painter.setPen(QColor("#1c2024"))
        painter.drawText(rect.adjusted(8, 10, -8, -4), Qt.AlignmentFlag.AlignRight, value)

    def _yes_no(self, row: FlightRLRow, key: str) -> str:
        if key not in row.values or row.values.get(key) == "":
            return "n/a"
        return "yes" if row.flag(key) else "no"

    def _fmt(self, value: float | None, suffix: str) -> str:
        if value is None:
            return "n/a"
        return f"{value:.2f}{suffix}" if suffix == "V" else f"{value:.0f}{suffix}"

    def _flag_color(self, row: FlightRLRow, key: str, good_when_true: bool) -> QColor:
        if key not in row.values or row.values.get(key) == "":
            return QColor("#cfd5dd")
        good = row.flag(key) == good_when_true
        return QColor("#2ea44f") if good else QColor("#d1242f")

    def _battery_color(self, value: float | None) -> QColor:
        if value is None:
            return QColor("#cfd5dd")
        if value < 3.65:
            return QColor("#d1242f")
        if value < 3.78:
            return QColor("#f59f00")
        return QColor("#2ea44f")

    def _rssi_color(self, value: float | None) -> QColor:
        if value is None:
            return QColor("#cfd5dd")
        return QColor("#2ea44f") if value > 70 else QColor("#f59f00")
