from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ecsers_analyzer.plotting.roi_regions import (
    clean_roi_role,
    normalize_roi_limits,
    parse_roi_limits,
    roi_default_label,
    should_auto_update_roi_label,
)


class RoiRegionsTests(unittest.TestCase):
    def test_normalize_roi_limits_orders_values(self):
        limits = normalize_roi_limits(1700, 400)

        self.assertEqual(limits.xmin, 400.0)
        self.assertEqual(limits.xmax, 1700.0)
        self.assertEqual(limits.width, 1300.0)

    def test_normalize_roi_limits_rejects_zero_width(self):
        with self.assertRaises(ValueError):
            normalize_roi_limits(500, 500)

    def test_parse_roi_limits_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            parse_roi_limits("bad", "600")

    def test_roi_default_label(self):
        self.assertEqual(
            roi_default_label("noise", 1800, 2000),
            "noise: 1800–2000 cm⁻¹",
        )

    def test_clean_roi_role_falls_back_to_peak(self):
        self.assertEqual(clean_roi_role("unknown"), "peak")

    def test_should_auto_update_roi_label(self):
        self.assertTrue(should_auto_update_roi_label("", "peak"))
        self.assertTrue(should_auto_update_roi_label("peak: 400–500 cm⁻¹", "peak"))
        self.assertTrue(should_auto_update_roi_label("noise: 1800–2000 cm⁻¹", "peak"))
        self.assertFalse(should_auto_update_roi_label("my custom region", "peak"))


if __name__ == "__main__":
    unittest.main()