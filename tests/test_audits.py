"""Run with: python -m unittest discover -s tests -v"""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_availability import audit  # noqa: E402
from evaluate_temporal import chronological_split, daily_features, metrics  # noqa: E402


class AvailabilityTests(unittest.TestCase):
    def test_committed_daily_series(self):
        summary, months = audit(ROOT / "data/smap_daily_means.csv")
        self.assertEqual((summary["total_days"], summary["valid_days"], summary["missing_days"]),
                         (300, 148, 152))
        self.assertEqual(len(months), 10)

    def test_missing_calendar_day_rejected(self):
        with tempfile.TemporaryDirectory() as dirname:
            file = Path(dirname) / "series.csv"
            file.write_text("date,SMAP_SM\n2021-01-01,0.2\n2021-01-03,\n")
            with self.assertRaises(ValueError):
                audit(file)


class EvaluationTests(unittest.TestCase):
    def test_aggregates_pixels_to_one_label_per_date(self):
        features = pd.DataFrame({"date": ["2021-01-01"] * 2 + ["2021-01-02"],
                                 "VV": [-10., -12., -999.],
                                 "VH": [-17., -19., -999.],
                                 "VHVV": [1.7, 1.58, 1.0],
                                 "NDVI": [.4, .6, -.1]})
        targets = pd.DataFrame({"date": ["2021-01-01", "2021-01-02"],
                                "SMAP_SM": [.25, None]})
        got = daily_features(features, targets)
        self.assertEqual(len(got), 2)
        self.assertNotIn("VHVV", got.columns)
        self.assertAlmostEqual(got.loc[0, "VV"], -11.)
        self.assertAlmostEqual(got.loc[0, "VH_minus_VV_dB"], -7.)
        self.assertTrue(pd.isna(got.loc[1, "VV"]))

    def test_chronological_split_never_uses_future_training(self):
        dates = pd.date_range("2021-01-01", periods=40, freq="D")
        data = pd.DataFrame({"date": dates, "SMAP_SM": [0.25] * len(dates)})
        train, val, test = chronological_split(data, "2021-02-01")
        self.assertLess(train.date.max(), val.date.min())
        self.assertLess(val.date.max(), test.date.min())
        self.assertEqual(len(train) + len(val) + len(test), 40)

    def test_zero_error_metrics(self):
        self.assertEqual(metrics([.1, .2, .3], [.1, .2, .3])["rmse_m3_m3"], 0)


if __name__ == "__main__":
    unittest.main()
