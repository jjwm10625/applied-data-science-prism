"""Score schema-compatible features without requiring future labels."""

import argparse
from pathlib import Path
import joblib
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--features", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    model = joblib.load(a.model)  # Only load trusted local artifacts.
    data = pd.read_csv(a.features, dtype={"user_key": "string"})
    if data.duplicated(["user_key", "reference_date"]).any():
        raise ValueError("Duplicate samples")
    out = data[["user_key", "reference_date"]].copy()
    out["probability"] = model["pipeline"].predict_proba(data[model["features"]])[:, 1]
    out["threshold"] = model["threshold"]
    out["predicted_label"] = (out.probability >= out.threshold).astype(int)
    out["window_days"] = model["window_days"]
    out["model"] = model["model"]
    out["seed"] = model["seed"]
    with Path(a.output).open("x") as f:
        out.to_csv(f, index=False)


if __name__ == "__main__":
    main()
