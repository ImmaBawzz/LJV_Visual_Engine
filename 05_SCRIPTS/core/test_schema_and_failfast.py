"""Unit tests for schema validation and checkpoint fail-fast output checks."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SchemaValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        (self.root / "01_CONFIG" / "schemas").mkdir(parents=True, exist_ok=True)
        (self.root / "03_WORK" / "reports").mkdir(parents=True, exist_ok=True)

        self.module: Any = _load_module(
            "schema_validator",
            Path(__file__).resolve().parent / "01c_validate_schemas.py",
        )

        self.old_config_dir = self.module.CONFIG_DIR
        self.old_report_path = self.module.REPORT_PATH
        self.module.CONFIG_DIR = self.root / "01_CONFIG"
        self.module.REPORT_PATH = self.root / "03_WORK" / "reports" / "schema_validation_report.json"

    def tearDown(self) -> None:
        self.module.CONFIG_DIR = self.old_config_dir
        self.module.REPORT_PATH = self.old_report_path
        self.tmp_dir.cleanup()

    def _write_json(self, relative: str, payload: dict[str, Any]) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def test_validate_file_reports_missing_required_key(self) -> None:
        self._write_json("01_CONFIG/sample.json", {"title": "ok"})
        self._write_json(
            "01_CONFIG/schemas/sample.schema.json",
            {
                "type": "object",
                "required": ["title", "artist"],
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "artist": {"type": "string", "minLength": 1},
                },
            },
        )

        ok, errors = self.module.validate_file("sample.json", "sample.schema.json")
        self.assertFalse(ok)
        self.assertTrue(any("missing required key 'artist'" in msg for msg in errors))


class CheckpointFailFastTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        (self.root / "03_WORK" / "logs").mkdir(parents=True, exist_ok=True)
        (self.root / "03_WORK" / "sections").mkdir(parents=True, exist_ok=True)
        (self.root / "04_OUTPUT" / "youtube_16x9").mkdir(parents=True, exist_ok=True)

        self.module: Any = _load_module(
            "checkpoint_manager_tested",
            Path(__file__).resolve().parent / "checkpoint_manager.py",
        )

        self.old_root = self.module.ROOT
        self.old_checkpoint = self.module.CHECKPOINT_FILE
        self.old_log = self.module.STRUCTURED_LOG

        self.module.ROOT = self.root
        self.module.CHECKPOINT_FILE = self.root / "03_WORK" / "pipeline_checkpoint.json"
        self.module.STRUCTURED_LOG = self.root / "03_WORK" / "logs" / "pipeline_execution.json"

    def tearDown(self) -> None:
        self.module.ROOT = self.old_root
        self.module.CHECKPOINT_FILE = self.old_checkpoint
        self.module.STRUCTURED_LOG = self.old_log
        self.tmp_dir.cleanup()

    def test_validate_step_output_raises_for_missing_master_render(self) -> None:
        cp = self.module.PipelineCheckpoint()
        with self.assertRaises(self.module.ValidationError):
            cp.validate_step_output(14)

    def test_validate_step_output_passes_when_master_render_exists(self) -> None:
        master = self.root / "04_OUTPUT" / "youtube_16x9" / "master_clean.mp4"
        master.write_bytes(b"0" * 2048)

        cp = self.module.PipelineCheckpoint()
        cp.validate_step_output(14)

    def test_validate_step_output_raises_for_invalid_timeline_json(self) -> None:
        timeline_path = self.root / "03_WORK" / "sections" / "timeline.json"
        timeline_path.write_text("not-json", encoding="utf-8")

        cp = self.module.PipelineCheckpoint()
        with self.assertRaises(self.module.ValidationError):
            cp.validate_step_output(10)


if __name__ == "__main__":
    unittest.main()
