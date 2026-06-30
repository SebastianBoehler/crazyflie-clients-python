from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from cfclient.ui.flightrl.log_model import DECISION_KEYS, FlightRLLog


TRACK_COLORS = {
    "emergency_active": QColor("#d1242f"),
    "escape_hold_active": QColor("#f59f00"),
    "direction_hold_active": QColor("#8250df"),
    "vertical_priority_active": QColor("#2da44e"),
    "shield_active": QColor("#0969da"),
    "raw_control_active": QColor("#bf3989"),
}


class DecisionTimelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._log: FlightRLLog | None = None
        self._row_index = 0
        self.setMinimumHeight(190)

    def set_log(self, log: FlightRLLog | None) -> None:
        self._log = log
        self._row_index = 0
        self.update()

    def set_row_index(self, index: int) -> None:
        self._row_index = max(0, index)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        self._draw_frame(painter)
        if self._log is None or not self._log.rows:
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No decision timeline")
            return
        keys = [key for key in DECISION_KEYS if key in self._log.fields]
        if not keys:
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "This log has no FlightRL decision flags")
            return
        self._draw_tracks(painter, keys)
        self._draw_cursor(painter)

    def _draw_frame(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#dde1e6"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.setPen(QColor("#5c6370"))
        painter.drawText(12, 22, "Decision Stack")

    def _draw_tracks(self, painter: QPainter, keys: list[str]) -> None:
        left = 154
        right = self.width() - 16
        top = 38
        track_h = 18
        gap = 9
        width = max(1, right - left)
        for row_num, key in enumerate(keys):
            y = top + row_num * (track_h + gap)
            label = key.replace("_active", "").replace("_", " ")
            painter.setPen(QColor("#5c6370"))
            painter.drawText(12, y + 14, label)
            painter.setPen(QPen(QColor("#ebedf0"), 1))
            painter.setBrush(QColor("#f6f7f9"))
            painter.drawRoundedRect(QRectF(left, y, width, track_h), 3, 3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(TRACK_COLORS.get(key, QColor("#3b7dd8")))
            for start, end in self._active_segments(key):
                x = left + width * start
                w = max(1.5, width * (end - start))
                painter.drawRoundedRect(QRectF(x, y + 2, w, track_h - 4), 2, 2)
            fraction = self._log.summary.active_fractions.get(key, 0.0)
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(right - 48, y + 14, f"{fraction * 100:.0f}%")

    def _active_segments(self, key: str) -> list[tuple[float, float]]:
        rows = self._log.rows
        if not rows:
            return []
        segments = []
        start = None
        total = len(rows)
        for index, row in enumerate(rows):
            active = row.flag(key)
            if active and start is None:
                start = index
            if start is not None and (not active or index == total - 1):
                end = index if not active else index + 1
                segments.append((start / total, end / total))
                start = None
        return segments

    def _draw_cursor(self, painter: QPainter) -> None:
        total = len(self._log.rows)
        fraction = self._row_index / max(1, total - 1)
        x = 154 + (self.width() - 170) * max(0.0, min(1.0, fraction))
        painter.setPen(QPen(QColor("#1c2024"), 2))
        painter.drawLine(int(x), 34, int(x), self.height() - 16)
