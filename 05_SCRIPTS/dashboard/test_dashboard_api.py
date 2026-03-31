"""Dashboard backend tests for control safety and state handling."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

import app as dashboard_app


class _FakeProcess:
    def __init__(self, pid: int = 4242):
        self.pid = pid


class DashboardApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

        (self.root / "03_WORK" / "logs").mkdir(parents=True, exist_ok=True)
        (self.root / "03_WORK" / "reports").mkdir(parents=True, exist_ok=True)
        (self.root / "03_WORK" / "analysis").mkdir(parents=True, exist_ok=True)
        (self.root / "04_OUTPUT").mkdir(parents=True, exist_ok=True)
        (self.root / "05_SCRIPTS").mkdir(parents=True, exist_ok=True)
        (self.root / "05_SCRIPTS" / "run_release_pipeline_resumable.ps1").write_text("# test", encoding="utf-8")

        self._old_values: dict[str, Any] = {
            "ROOT": dashboard_app.ROOT,
            "WORK_DIR": dashboard_app.WORK_DIR,
            "LOGS_DIR": dashboard_app.LOGS_DIR,
            "REPORTS_DIR": dashboard_app.REPORTS_DIR,
            "ANALYSIS_DIR": dashboard_app.ANALYSIS_DIR,
            "OUTPUT_DIR": dashboard_app.OUTPUT_DIR,
            "CHECKPOINT_FILE": dashboard_app.CHECKPOINT_FILE,
            "STRUCTURED_LOG": dashboard_app.STRUCTURED_LOG,
            "DELIVERY_MANIFEST": dashboard_app.DELIVERY_MANIFEST,
            "PIPELINE_RUNNER": dashboard_app.PIPELINE_RUNNER,
            "RUNTIME_STATE_FILE": dashboard_app.RUNTIME_STATE_FILE,
            "CONTROL_COOLDOWN_SEC": dashboard_app.CONTROL_COOLDOWN_SEC,
        }

        dashboard_app.ROOT = self.root
        dashboard_app.WORK_DIR = self.root / "03_WORK"
        dashboard_app.LOGS_DIR = dashboard_app.WORK_DIR / "logs"
        dashboard_app.REPORTS_DIR = dashboard_app.WORK_DIR / "reports"
        dashboard_app.ANALYSIS_DIR = dashboard_app.WORK_DIR / "analysis"
        dashboard_app.OUTPUT_DIR = self.root / "04_OUTPUT"
        dashboard_app.CHECKPOINT_FILE = dashboard_app.WORK_DIR / "pipeline_checkpoint.json"
        dashboard_app.STRUCTURED_LOG = dashboard_app.LOGS_DIR / "pipeline_execution.json"
        dashboard_app.DELIVERY_MANIFEST = dashboard_app.OUTPUT_DIR / "delivery_manifest.json"
        dashboard_app.PIPELINE_RUNNER = self.root / "05_SCRIPTS" / "run_release_pipeline_resumable.ps1"
        dashboard_app.RUNTIME_STATE_FILE = dashboard_app.LOGS_DIR / "dashboard_runtime_state.json"
        dashboard_app.CONTROL_COOLDOWN_SEC = 0

    def tearDown(self) -> None:
        for key, value in self._old_values.items():
            setattr(dashboard_app, key, value)
        self.tmp_dir.cleanup()

    def test_retry_requires_failed_step(self) -> None:
        dashboard_app._safe_write_json(
            dashboard_app.CHECKPOINT_FILE,
            {
                "overall_status": "in_progress",
                "steps": {"1": {"status": "completed"}},
            },
        )

        with self.assertRaises(dashboard_app.HTTPException) as exc:
            dashboard_app._start_pipeline("retry")

        self.assertEqual(exc.exception.status_code, 409)

    def test_retry_uses_resume_mode_when_failed_step_exists(self) -> None:
        dashboard_app._safe_write_json(
            dashboard_app.CHECKPOINT_FILE,
            {
                "overall_status": "failed",
                "steps": {
                    "1": {"status": "completed"},
                    "2": {"status": "failed"},
                },
            },
        )

        captured: dict[str, list[str]] = {"args": []}
        old_popen = dashboard_app.subprocess.Popen

        def _fake_popen(args, **kwargs):  # type: ignore[no-untyped-def]
            captured["args"] = [str(item) for item in args]
            return _FakeProcess()

        dashboard_app.subprocess.Popen = _fake_popen  # type: ignore[assignment]
        try:
            runtime = dashboard_app._start_pipeline("retry")
        finally:
            dashboard_app.subprocess.Popen = old_popen  # type: ignore[assignment]

        self.assertTrue(runtime["active"])
        self.assertEqual(runtime["mode"], "retry")
        self.assertIn("-Resume", captured["args"])

    def test_refresh_runtime_marks_inactive_if_pid_not_running(self) -> None:
        dashboard_app._safe_write_json(
            dashboard_app.RUNTIME_STATE_FILE,
            {
                "active": True,
                "pid": 99999,
                "mode": "start",
                "started_at": dashboard_app._utc_now(),
                "last_exit_code": None,
                "last_action": "start:start",
            },
        )
        dashboard_app._safe_write_json(
            dashboard_app.CHECKPOINT_FILE,
            {
                "overall_status": "failed",
                "steps": {"1": {"status": "failed"}},
            },
        )

        old_is_pid_running = dashboard_app._is_pid_running
        dashboard_app._is_pid_running = lambda pid: False  # type: ignore[assignment]
        try:
            refreshed = dashboard_app._refresh_runtime_state()
        finally:
            dashboard_app._is_pid_running = old_is_pid_running  # type: ignore[assignment]

        self.assertFalse(refreshed["active"])
        self.assertEqual(refreshed["last_exit_code"], 1)

    def test_logs_cursor_window(self) -> None:
        entries = [
            {"timestamp": "t1", "level": "INFO", "step": "A", "message": "one", "exit_code": 0},
            {"timestamp": "t2", "level": "INFO", "step": "B", "message": "two", "exit_code": 0},
            {"timestamp": "t3", "level": "ERROR", "step": "C", "message": "three", "exit_code": 1},
        ]
        dashboard_app._safe_write_json(dashboard_app.STRUCTURED_LOG, entries)

        payload = dashboard_app.logs(cursor=1, limit=2)
        self.assertEqual(payload["cursor"], 1)
        self.assertEqual(payload["next_cursor"], 3)
        self.assertEqual(payload["total"], 3)
        self.assertEqual(len(payload["entries"]), 2)
        self.assertEqual(payload["entries"][0]["message"], "two")

    def test_state_exposes_control_flags(self) -> None:
        dashboard_app._safe_write_json(
            dashboard_app.CHECKPOINT_FILE,
            {
                "overall_status": "failed",
                "steps": {
                    "1": {"status": "completed", "name": "Step 1"},
                    "2": {"status": "failed", "name": "Step 2"},
                },
            },
        )
        dashboard_app._safe_write_json(
            dashboard_app.RUNTIME_STATE_FILE,
            {
                "active": False,
                "pid": None,
                "mode": None,
                "started_at": None,
                "last_exit_code": 1,
                "last_action": "start:retry",
            },
        )

        payload = dashboard_app.state()
        self.assertTrue(payload["controls"]["can_start"])
        self.assertTrue(payload["controls"]["can_resume"])
        self.assertTrue(payload["controls"]["can_retry"])
        self.assertTrue(payload["controls"]["has_failed_step"])


if __name__ == "__main__":
    unittest.main()
