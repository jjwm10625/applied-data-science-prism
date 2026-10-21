"""One shared temporal split and 7-day boundary purge for all windows."""

from prism.legacy import module


def temporal_split(data, settings):
    if not settings.get("validation_start") or not settings.get("test_start"):
        raise ValueError(
            "Team must agree validation_start and test_start before training"
        )
    if settings.get("label_horizon_days", 7) != 7:
        raise ValueError("This dataset has 7-day labels")
    result = data.copy()
    result["split"] = module("run").assign_split(result, {"split_dates": settings})
    return result
