import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from prism.split import temporal_split
from prism.train import train, choose_threshold
from prism.evaluate import metrics, evaluate
from prism.personalize import analyze


class TeamTests(unittest.TestCase):
    def test_split_requires_agreement_and_purges(self):
        f = pd.DataFrame(
            {
                "reference_date": [
                    "2026-01-20",
                    "2026-01-28",
                    "2026-02-01",
                    "2026-02-26",
                    "2026-03-01",
                ]
            }
        )
        with self.assertRaises(ValueError):
            temporal_split(f, {"validation_start": None})
        s = temporal_split(
            f, {"validation_start": "2026-02-01", "test_start": "2026-03-01"}
        )
        self.assertEqual(
            s.split.tolist(),
            [
                "train",
                "purged_label_overlap",
                "validation",
                "purged_label_overlap",
                "test",
            ],
        )

    def test_metrics_threshold_equality_and_invalid_probabilities(self):
        r = metrics([0, 1, 1], [0.2, 0.5, 0.9], 0.5)
        self.assertEqual(r["f1"], 1)
        with self.assertRaises(ValueError):
            metrics([0, 1], [0, np.inf], 0.5)
        self.assertTrue(0 <= choose_threshold([0, 1], [0.1, 0.9]) <= 1)

    def test_synthetic_train_evaluate_and_same_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            f = pd.DataFrame(
                {
                    "user_key": ["fake"] * 90,
                    "reference_date": pd.date_range("2026-01-01", periods=90).strftime(
                        "%Y-%m-%d"
                    ),
                    "label_proxy_churn_7d": [i % 2 for i in range(90)],
                    "w7__x": [i % 2 for i in range(90)],
                    "w28__x": [i % 2 for i in range(90)],
                }
            )
            f.to_csv(p / "data.csv", index=False)
            (p / "roles.json").write_text(
                json.dumps(
                    {
                        "target": "label_proxy_churn_7d",
                        "model_columns_by_window": {"7": ["w7__x"], "28": ["w28__x"]},
                        "definition": "synthetic proxy",
                    }
                )
            )
            (p / "split.json").write_text(
                json.dumps(
                    {"validation_start": "2026-02-01", "test_start": "2026-03-01"}
                )
            )
            (p / "config.json").write_text(
                json.dumps(
                    {
                        "dataset": str(p / "data.csv"),
                        "roles": str(p / "roles.json"),
                        "split_config": str(p / "split.json"),
                        "windows": [7, 28],
                        "models": ["logistic_regression", "random_forest"],
                        "seeds": [11],
                    }
                )
            )
            train(p / "config.json", p / "models")
            evaluate(p / "models", p / "evaluation")
            result = pd.read_csv(p / "evaluation/metrics.csv")
            self.assertEqual(len(result), 12)
            self.assertTrue(result.f1.between(0, 1).all())
            self.assertEqual(len(list((p / "models").glob("*.joblib"))), 4)
            self.assertTrue((p / "models/split_exclusions.csv").exists())
            self.assertTrue((p / "evaluation/calibration.csv").exists())

    def test_personalization_fallback_future_and_midnight(self):
        cfg = {
            "window_days": 28,
            "min_session_days": 3,
            "min_weekday_days": 3,
            "min_feature_days": 3,
            "time_band_hours": 3,
            "templates": {"diary": {"body": "test", "route": "diary_write"}},
        }
        rows = []
        for i, d in enumerate(["2026-01-05", "2026-01-06", "2026-01-07", "2026-02-01"]):
            rows.append(
                {
                    "user_key": "fake",
                    "device_key": "d",
                    "session_id": str(i + 1),
                    "session_valid": True,
                    "active_event": 1,
                    "event_type": "click_write_diary.textfield",
                    "event_time_utc": d + "T14:00:00Z",
                }
            )
        result = analyze(pd.DataFrame(rows), "2026-01-10", cfg)
        self.assertEqual(len(result), 7)
        self.assertTrue(result.eligible.all())
        self.assertTrue(result.session_support_days.eq(3).all())
        self.assertTrue(result.time_source.eq("overall_fallback").all())
        self.assertTrue(result.notify_hour.eq(0).all())
        self.assertTrue(result.notify_day_offset.eq(1).all())
        short = analyze(pd.DataFrame(rows[:1]), "2026-01-10", cfg)
        self.assertFalse(short.eligible.any())


if __name__ == "__main__":
    unittest.main()
