"""Owner: 박주현. Report fixed-threshold metrics and seed variability."""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    average_precision_score,
    brier_score_loss,
)


def metrics(y, probabilities, threshold):
    y = np.asarray(y)
    p = np.asarray(probabilities, dtype=float)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probability outside [0,1]")
    if not np.isin(y, [0, 1]).all() or not 0 <= threshold <= 1:
        raise ValueError("Invalid target or threshold")
    pred = p >= threshold
    return {
        "f1": f1_score(y, pred, zero_division=0),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "pr_auc_ap": (
            average_precision_score(y, p) if len(np.unique(y)) == 2 else np.nan
        ),
        "brier_score": brier_score_loss(y, p),
        "rows": len(y),
    }


def evaluate(source, output):
    files = sorted(Path(source).glob("*_predictions.csv"))
    if not files:
        raise ValueError("No prediction files")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    calibration = []
    common = {}
    for path in files:
        f = pd.read_csv(path)
        if f.duplicated(["user_key", "reference_date", "split"]).any():
            raise ValueError("Duplicate prediction sample")
        for split, g in f.groupby("split"):
            keys = (
                g[["user_key", "reference_date", "y_true"]]
                .sort_values(["user_key", "reference_date"])
                .reset_index(drop=True)
            )
            if split in common:
                pd.testing.assert_frame_equal(keys, common[split])
            else:
                common[split] = keys
            if g.threshold.nunique() != 1:
                raise ValueError("Threshold must be fixed per model")
            info = {
                c: g[c].iloc[0] for c in ["model", "window_days", "seed", "threshold"]
            }
            info["split"] = split
            rows.append({**info, **metrics(g.y_true, g.probability, info["threshold"])})
            bins = pd.cut(g.probability, np.linspace(0, 1, 11), include_lowest=True)
            for band, b in g.groupby(bins, observed=True):
                calibration.append(
                    {
                        **info,
                        "bin": str(band),
                        "rows": len(b),
                        "mean_probability": b.probability.mean(),
                        "observed_proxy_rate": b.y_true.mean(),
                    }
                )
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "metrics.csv", index=False)
    names = ["f1", "precision", "recall", "pr_auc_ap", "brier_score"]
    frame.groupby(["model", "window_days", "split"])[names].agg(
        ["mean", "std", "count"]
    ).to_csv(output / "metrics_summary.csv")
    pd.DataFrame(calibration).to_csv(output / "calibration.csv", index=False)
    (output / "README.txt").write_text(
        "PR-AUC is average precision (AP). Seed std is pandas sample std (ddof=1). Test is reporting only; select model/threshold with validation. Target is telemetry proxy, not verified real inactivity.\n"
    )
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--predictions", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    print(evaluate(a.predictions, a.output))


if __name__ == "__main__":
    main()
