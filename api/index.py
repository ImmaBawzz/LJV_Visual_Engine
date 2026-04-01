from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "05_SCRIPTS" / "dashboard" / "app.py"


def _load_dashboard_app():
    spec = importlib.util.spec_from_file_location("ljv_dashboard_app", APP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load dashboard app from {APP_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "app"):
        raise RuntimeError("Dashboard module did not expose a FastAPI 'app' object")

    return module.app


app = _load_dashboard_app()
