"""Owner: 이다은. Fit on train; select thresholds exclusively on validation."""

import argparse
import json
import hashlib
import platform
import importlib.metadata
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from prism.legacy import ROOT, module
from prism.load_data import load_modeling
from prism.split import temporal_split


def estimator(name, seed):
    if name == "logistic_regression":
        return LogisticRegression(max_iter=2000, random_state=seed)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=300, random_state=seed, n_jobs=-1)
    if name == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=300, random_state=seed, eval_metric="logloss", n_jobs=2
        )
    if name == "catboost":
        from catboost import CatBoostClassifier

        return CatBoostClassifier(
            iterations=300, random_seed=seed, verbose=False, allow_writing_files=False
        )
    raise ValueError("Unknown model: " + name)


def choose_threshold(y, probabilities):
    # Fixed grid; smallest distance to 0.5 then lower threshold breaks F1 ties.
    candidates = np.linspace(0, 1, 201)
    return float(
        max(
            candidates,
            key=lambda t: (
                f1_score(y, probabilities >= t, zero_division=0),
                -abs(t - 0.5),
                -t,
            ),
        )
    )


def train(config_path, output):
    cfg = json.loads(Path(config_path).read_text())
    data, roles = load_modeling(ROOT / cfg["dataset"], ROOT / cfg["roles"])
    settings = json.loads((ROOT / cfg["split_config"]).read_text())
    data = temporal_split(data, settings)
    target = roles["target"]
    groups = {s: data[data.split.eq(s)] for s in ["train", "validation", "test"]}
    if any(g.empty for g in groups.values()):
        raise ValueError("All three temporal intervals must contain samples")
    if any(g[target].nunique() != 2 for g in groups.values()):
        raise ValueError("Each temporal interval must contain both classes")
    if not cfg["windows"] or not cfg["models"] or not cfg["seeds"]:
        raise ValueError("Empty experiment grid")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    excluded = data[data.split.eq("purged_label_overlap")]
    excluded.to_csv(output / "split_exclusions.csv", index=False)
    data[["user_key", "reference_date", "split"]].to_csv(
        output / "sample_splits.csv", index=False
    )
    digest = hashlib.sha256((ROOT / cfg["dataset"]).read_bytes()).hexdigest()
    for window in cfg["windows"]:
        cols = roles["model_columns_by_window"][str(window)]
        for name in cfg["models"]:
            for seed in cfg["seeds"]:
                pre = module("model_transform").make_preprocessor(
                    cols, scale=name == "logistic_regression"
                )
                model = Pipeline(
                    [("preprocessor", pre), ("classifier", estimator(name, seed))]
                )
                model.fit(groups["train"][cols], groups["train"][target])
                val = model.predict_proba(groups["validation"][cols])[:, 1]
                threshold = choose_threshold(groups["validation"][target], val)
                tag = f"{name}_w{window}_seed{seed}"
                artifact = {
                    "pipeline": model,
                    "features": cols,
                    "target": target,
                    "threshold": threshold,
                    "model": name,
                    "window_days": window,
                    "seed": seed,
                    "split_settings": settings,
                    "dataset_sha256": digest,
                    "target_definition": roles["definition"],
                    "experiment": cfg,
                    "environment": {
                        "python": platform.python_version(),
                        **{
                            n: importlib.metadata.version(n)
                            for n in ["numpy", "pandas", "scikit-learn", "joblib"]
                        },
                    },
                }
                joblib.dump(artifact, output / (tag + ".joblib"))
                rows = []
                for split, g in groups.items():
                    p = model.predict_proba(g[cols])[:, 1]
                    f = g[["user_key", "reference_date"]].copy()
                    f["y_true"] = g[target].to_numpy()
                    f["probability"] = p
                    f["threshold"] = threshold
                    f["predicted_label"] = (p >= threshold).astype(int)
                    f["split"] = split
                    f["model"] = name
                    f["window_days"] = window
                    f["seed"] = seed
                    rows.append(f)
                pd.concat(rows).to_csv(output / (tag + "_predictions.csv"), index=False)
    (output / "experiment.json").write_text(
        json.dumps(
            {"config": cfg, "splits": settings, "dataset_sha256": digest}, indent=2
        )
    )
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(ROOT / "configs/experiment.json"))
    p.add_argument("--output", required=True)
    a = p.parse_args()
    print(train(a.config, a.output))


if __name__ == "__main__":
    main()
