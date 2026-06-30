from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfclient.ui.flightrl.log_model import load_log, parse_flag  # noqa: E402


class FlightRLLogModelTest(unittest.TestCase):
    def test_load_log_summarizes_ranges_flags_and_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flight.csv"
            path.write_text(
                "host_time_s,range.front,range.back,range.left,range.right,"
                "stateEstimate.vx,stateEstimate.vy,vx_m_s,vy_m_s,"
                "emergency_active,shield_active,pm.vbat,sys.canfly,"
                "sys.isTumbled,health.motorPass,health.batteryPass\n"
                "1.0,32766,1000,,500,3.0,4.0,0.1,0.2,0,False,3.9,1,0,1,1\n"
                "3.0,250,32766,700,800,,,0.3,0.4,1,True,3.7,0,1,0,0\n"
            )

            log = load_log(path)

        self.assertEqual(2, log.summary.row_count)
        self.assertEqual(16, log.summary.columns)
        self.assertEqual(2.0, log.summary.duration_s)
        self.assertIn("range", log.summary.field_groups)
        self.assertIn("safety", log.summary.field_groups)
        self.assertAlmostEqual(0.25, log.summary.min_horizontal_range_m)
        self.assertAlmostEqual(5.0, log.summary.max_horizontal_speed_m_s)
        self.assertAlmostEqual(0.5, log.summary.max_command_speed_m_s)
        self.assertAlmostEqual(3.7, log.summary.battery_min_v)
        self.assertAlmostEqual(3.7, log.summary.battery_latest_v)
        self.assertAlmostEqual(0.5, log.summary.active_fractions["emergency_active"])
        self.assertAlmostEqual(0.5, log.summary.active_fractions["shield_active"])
        self.assertEqual(
            ("canfly blocked", "tumbled", "motor health failed", "battery health failed"),
            log.summary.health_warnings,
        )

    def test_row_access_handles_open_range_and_fraction_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flight.csv"
            path.write_text("host_time_s,range.front\n1.0,32766\n2.0,250\n3.0,\n")
            log = load_log(path)

        self.assertAlmostEqual(4.0, log.rows[0].range_m("range.front"))
        self.assertAlmostEqual(0.25, log.rows[1].range_m("range.front"))
        self.assertIsNone(log.rows[2].range_m("range.front"))
        self.assertEqual(0, log.row_at_fraction(-1.0).index)
        self.assertEqual(2, log.row_at_fraction(2.0).index)

    def test_parse_flag_accepts_strings_and_numeric_values(self) -> None:
        self.assertTrue(parse_flag("true"))
        self.assertTrue(parse_flag("1"))
        self.assertTrue(parse_flag(2.0))
        self.assertFalse(parse_flag("false"))
        self.assertFalse(parse_flag("0"))
        self.assertFalse(parse_flag(""))


if __name__ == "__main__":
    unittest.main()
