from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

OPEN_RANGE_RAW = 32000.0
OPEN_RANGE_M = 4.0

HORIZONTAL_RANGE_KEYS = ("range.front", "range.back", "range.left", "range.right")
VERTICAL_RANGE_KEYS = ("range.up", "range.zrange")
DECISION_KEYS = (
    "emergency_active",
    "escape_hold_active",
    "direction_hold_active",
    "vertical_priority_active",
    "shield_active",
    "raw_control_active",
)

FIELD_GROUPS = {
    "range": (*HORIZONTAL_RANGE_KEYS, *VERTICAL_RANGE_KEYS),
    "pose": ("stateEstimate.x", "stateEstimate.y", "stateEstimate.z", "stabilizer.yaw"),
    "velocity": ("stateEstimate.vx", "stateEstimate.vy", "stateEstimate.vz"),
    "command": ("vx_m_s", "vy_m_s", "vz_m_s", "yawrate_deg_s"),
    "raw command": ("raw_vx_m_s", "raw_vy_m_s", "raw_yawrate_deg_s", "thrust_percent"),
    "puffer action": ("action_thrust", "action_roll_rate", "action_pitch_rate", "action_yaw_rate"),
    "safety": DECISION_KEYS,
    "power": ("pm.vbat", "pm.batteryLevel", "pm.state"),
    "radio": ("radio.rssi", "radio.isConnected", "radio.numRxUc", "radio.numRxBc"),
    "motors": ("motor.m1", "motor.m2", "motor.m3", "motor.m4", "rpm.m1", "rpm.m2", "rpm.m3", "rpm.m4"),
    "health": ("sys.canfly", "sys.isFlying", "sys.isTumbled", "health.motorPass", "health.batteryPass"),
}


@dataclass(frozen=True, slots=True)
class FlightRLRow:
    index: int
    values: dict[str, str]

    def number(self, key: str, default: float | None = None) -> float | None:
        return parse_number(self.values.get(key), default)

    def flag(self, key: str) -> bool:
        return parse_flag(self.values.get(key))

    def range_m(self, key: str) -> float | None:
        raw = self.number(key)
        if raw is None:
            return None
        return OPEN_RANGE_M if raw >= OPEN_RANGE_RAW else max(0.0, raw / 1000.0)

    def horizontal_range_m(self) -> float | None:
        ranges = [self.range_m(key) for key in HORIZONTAL_RANGE_KEYS]
        ranges = [value for value in ranges if value is not None]
        return min(ranges) if ranges else None

    def horizontal_speed_m_s(self) -> float | None:
        vx = self.number("stateEstimate.vx")
        vy = self.number("stateEstimate.vy")
        if vx is None or vy is None:
            vx = self.number("vx_m_s")
            vy = self.number("vy_m_s")
        if vx is None or vy is None:
            return None
        return math.hypot(vx, vy)

    def command_speed_m_s(self) -> float | None:
        vx = self.number("vx_m_s")
        vy = self.number("vy_m_s")
        if vx is None or vy is None:
            return None
        return math.hypot(vx, vy)


@dataclass(frozen=True, slots=True)
class LogSummary:
    row_count: int
    duration_s: float
    columns: int
    field_groups: tuple[str, ...]
    min_horizontal_range_m: float | None
    max_horizontal_speed_m_s: float | None
    max_command_speed_m_s: float | None
    battery_min_v: float | None
    battery_latest_v: float | None
    active_fractions: dict[str, float]
    health_warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FlightRLLog:
    path: Path
    fields: tuple[str, ...]
    rows: tuple[FlightRLRow, ...]
    summary: LogSummary

    def row_at_fraction(self, fraction: float) -> FlightRLRow | None:
        if not self.rows:
            return None
        index = round(max(0.0, min(1.0, fraction)) * (len(self.rows) - 1))
        return self.rows[index]


def load_log(path: str | Path) -> FlightRLLog:
    source = Path(path)
    with source.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = tuple(reader.fieldnames or ())
        rows = tuple(FlightRLRow(index, dict(row)) for index, row in enumerate(reader))
    return FlightRLLog(source, fields, rows, summarize(fields, rows))


def summarize(fields: tuple[str, ...], rows: tuple[FlightRLRow, ...]) -> LogSummary:
    groups = tuple(name for name, keys in FIELD_GROUPS.items() if any(key in fields for key in keys))
    return LogSummary(
        row_count=len(rows),
        duration_s=_duration(rows),
        columns=len(fields),
        field_groups=groups,
        min_horizontal_range_m=_min_value(row.horizontal_range_m() for row in rows),
        max_horizontal_speed_m_s=_max_value(row.horizontal_speed_m_s() for row in rows),
        max_command_speed_m_s=_max_value(row.command_speed_m_s() for row in rows),
        battery_min_v=_min_value(row.number("pm.vbat") for row in rows),
        battery_latest_v=_latest_number(rows, "pm.vbat"),
        active_fractions={key: _active_fraction(rows, key) for key in DECISION_KEYS if key in fields},
        health_warnings=_health_warnings(rows[-1] if rows else None),
    )


def parse_number(raw: object, default: float | None = None) -> float | None:
    try:
        if raw in ("", None):
            return default
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(value) else value


def parse_flag(raw: object) -> bool:
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in ("true", "yes", "on"):
            return True
        if lowered in ("false", "no", "off", ""):
            return False
    value = parse_number(raw, 0.0)
    return bool(value and value > 0.5)


def _duration(rows: tuple[FlightRLRow, ...]) -> float:
    times = [row.number("host_time_s") for row in rows]
    times = [value for value in times if value is not None]
    if len(times) < 2:
        return 0.0
    return max(times) - min(times)


def _active_fraction(rows: tuple[FlightRLRow, ...], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.flag(key)) / len(rows)


def _health_warnings(row: FlightRLRow | None) -> tuple[str, ...]:
    if row is None:
        return ()
    warnings: list[str] = []
    for key, label in (
        ("sys.canfly", "canfly blocked"),
        ("sys.isTumbled", "tumbled"),
        ("health.motorPass", "motor health failed"),
        ("health.batteryPass", "battery health failed"),
    ):
        if key == "sys.isTumbled" and row.flag(key):
            warnings.append(label)
        elif key != "sys.isTumbled" and key in row.values and not row.flag(key):
            warnings.append(label)
    return tuple(warnings)


def _latest_number(rows: tuple[FlightRLRow, ...], key: str) -> float | None:
    for row in reversed(rows):
        value = row.number(key)
        if value is not None:
            return value
    return None


def _min_value(values) -> float | None:
    clean = [value for value in values if value is not None]
    return min(clean) if clean else None


def _max_value(values) -> float | None:
    clean = [value for value in values if value is not None]
    return max(clean) if clean else None
