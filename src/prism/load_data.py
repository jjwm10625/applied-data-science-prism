"""Validated modeling input; raw event loading remains in pipeline/run.py."""

import json
from pathlib import Path
import numpy as np
import pandas as pd


def load_modeling(dataset, roles_path):
    data = pd.read_csv(
        dataset, dtype={"user_key": "string"}, float_precision="round_trip"
    )
    roles = json.loads(Path(roles_path).read_text())
    required = ["user_key", "reference_date", roles["target"]]
    features = sum(roles["model_columns_by_window"].values(), [])
    if set(required + features) - set(data):
        raise ValueError("Dataset schema does not match feature_roles.json")
    if (
        data[required].isna().any().any()
        or data.duplicated(["user_key", "reference_date"]).any()
    ):
        raise ValueError("Missing management fields or duplicate samples")
    if not data[roles["target"]].isin([0, 1]).all():
        raise ValueError("Modeling requires known binary labels")
    if np.isinf(data[features].to_numpy(dtype=float)).any():
        raise ValueError("Infinite features")
    for cols in roles["model_columns_by_window"].values():
        if any(c.startswith(("label_", "q")) or c in required for c in cols):
            raise ValueError("Management/quality/target in candidate list")
    return data, roles


def event_chunks(path, columns=None, chunksize=100000):
    return pd.read_csv(
        path,
        usecols=columns,
        chunksize=chunksize,
        dtype={"user_key": "string", "device_key": "string", "session_id": "string"},
    )
