from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from cfclient.ui.flightrl.log_model import FlightRLRow, HORIZONTAL_RANGE_KEYS, OPEN_RANGE_M


class RangerBubbleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._row: FlightRLRow | None = None
        self.setMinimumSize(280, 240)

    def set_row(self, row: FlightRLRow | None) -> None:
        self._row = row
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        self._draw_frame(painter)
        if self._row is None:
            self._draw_empty(painter)
            return
        center = QPointF(self.width() * 0.42, self.height() * 0.52)
        radius = min(self.width() * 0.34, self.height() * 0.38)
        self._draw_drone(painter, center)
        self._draw_ranges(painter, center, radius)
        self._draw_velocity(painter, center, radius)
        self._draw_vertical(painter)

    def _draw_frame(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#dde1e6"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.setPen(QColor("#5c6370"))
        painter.drawText(12, 22, "Ranger Bubble")

    def _draw_empty(self, painter: QPainter) -> None:
        painter.setPen(QColor("#9ca3af"))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Load a FlightRL CSV log")

    def _draw_drone(self, painter: QPainter, center: QPointF) -> None:
        painter.setPen(QPen(QColor("#1c2024"), 2))
        painter.setBrush(QColor("#f6f7f9"))
        painter.drawEllipse(center, 12, 12)
        painter.drawLine(QPointF(center.x() - 24, center.y()), QPointF(center.x() + 24, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - 24), QPointF(center.x(), center.y() + 24))

    def _draw_ranges(self, painter: QPainter, center: QPointF, radius: float) -> None:
        directions = {
            "range.front": QPointF(0, -1),
            "range.back": QPointF(0, 1),
            "range.left": QPointF(-1, 0),
            "range.right": QPointF(1, 0),
        }
        for key in HORIZONTAL_RANGE_KEYS:
            value = self._row.range_m(key)
            if value is None:
                continue
            unit = directions[key]
            length = radius * min(value, OPEN_RANGE_M) / OPEN_RANGE_M
            end = QPointF(center.x() + unit.x() * length, center.y() + unit.y() * length)
            painter.setPen(QPen(self._range_color(value), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(center, end)
            painter.setPen(QColor("#5c6370"))
            painter.drawText(QPointF(end.x() + 6, end.y() - 4), f"{key.split('.')[1]} {value:.2f}m")

    def _draw_velocity(self, painter: QPainter, center: QPointF, radius: float) -> None:
        vx = self._row.number("stateEstimate.vx", self._row.number("vx_m_s", 0.0)) or 0.0
        vy = self._row.number("stateEstimate.vy", self._row.number("vy_m_s", 0.0)) or 0.0
        scale = min(radius * 0.75, 80.0)
        end = QPointF(center.x() + vy * scale, center.y() - vx * scale)
        painter.setPen(QPen(QColor("#3b7dd8"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(center, end)
        painter.setBrush(QColor("#3b7dd8"))
        painter.drawEllipse(end, 4, 4)

    def _draw_vertical(self, painter: QPainter) -> None:
        x = self.width() - 82
        top = 48
        height = self.height() - 86
        painter.setPen(QPen(QColor("#dde1e6"), 1))
        painter.drawRect(x, top, 18, height)
        for key, label in (("range.up", "up"), ("range.zrange", "floor")):
            value = self._row.range_m(key)
            if value is None:
                continue
            fill = int(height * min(value, OPEN_RANGE_M) / OPEN_RANGE_M)
            y = top + height - fill
            painter.fillRect(x + 2, y, 14, fill, self._range_color(value))
            painter.setPen(QColor("#5c6370"))
            painter.drawText(x + 26, y + 12, f"{label} {value:.2f}m")

    def _range_color(self, value_m: float) -> QColor:
        if value_m < 0.25:
            return QColor("#d1242f")
        if value_m < 0.45:
            return QColor("#f59f00")
        if value_m >= OPEN_RANGE_M:
            return QColor("#cfd5dd")
        return QColor("#2ea44f")
