"""Load existing sibling-import pipeline without relocating its files."""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "pipeline"


def module(name):
    if str(PIPELINE) not in sys.path:
        sys.path.insert(0, str(PIPELINE))
    result = importlib.import_module(name)
    if Path(result.__file__).resolve().parent != PIPELINE:
        raise ImportError("Unexpected legacy module origin: " + name)
    return result
