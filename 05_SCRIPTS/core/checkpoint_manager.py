"""
Pipeline Checkpoint Manager

Enables resumable runs by tracking step completion status, timing, and errors.
Stores state in JSON for cross-script access.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_FILE = ROOT / "03_WORK" / "pipeline_checkpoint.json"
STRUCTURED_LOG = ROOT / "03_WORK" / "logs" / "pipeline_execution.json"


class ValidationError(Exception):
    """Raised when a pipeline step output fails validation."""


def _utc_now_iso() -> str:
    """Return a timezone-aware UTC ISO timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_or_now(value: Optional[str]) -> datetime:
    """Parse an ISO datetime string, defaulting to UTC now when invalid or missing."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return datetime.now(timezone.utc)


def _ensure_dirs():
    """Ensure required directories exist."""
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    STRUCTURED_LOG.parent.mkdir(parents=True, exist_ok=True)


class PipelineCheckpoint:
    """Manages pipeline checkpoint state and structured logging."""

    def __init__(self):
        """Initialize checkpoint manager."""
        _ensure_dirs()
        self.state = self._load()
        self._log_file = STRUCTURED_LOG

    def _load(self) -> Dict[str, Any]:
        """Load checkpoint state from file, or create empty state."""
        if CHECKPOINT_FILE.exists():
            try:
                data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
                # Convert string step IDs back to integers
                if "steps" in data and isinstance(data["steps"], dict):
                    data["steps"] = {int(k): v for k, v in data["steps"].items()}
                return data
            except Exception as e:
                print(f"Warning: Could not load checkpoint ({e}), starting fresh.")
                return self._create_empty_state()
        return self._create_empty_state()

    @staticmethod
    def _create_empty_state() -> Dict[str, Any]:
        """Create new empty checkpoint state."""
        return {
            "pipeline_version": "1.0",
            "created_at": _utc_now_iso(),
            "last_updated": _utc_now_iso(),
            "overall_status": "in_progress",
            "steps": {}
        }

    def save(self) -> None:
        """Persist checkpoint state to disk."""
        self.state["last_updated"] = _utc_now_iso()
        # Convert integer keys to strings for JSON serialization
        save_data = self.state.copy()
        if "steps" in save_data:
            save_data["steps"] = {str(k): v for k, v in save_data["steps"].items()}
        CHECKPOINT_FILE.write_text(json.dumps(save_data, indent=2), encoding="utf-8")

    def mark_step_started(self, step_id: int, step_name: str) -> None:
        """Record that a step is starting."""
        if step_id not in self.state["steps"]:
            self.state["steps"][step_id] = {
                "name": step_name,
                "status": "pending",
                "start_time": None,
                "end_time": None,
                "duration_sec": None,
                "exit_code": None,
                "error": None
            }

        self.state["steps"][step_id]["status"] = "running"
        self.state["steps"][step_id]["start_time"] = _utc_now_iso()
        self.state["overall_status"] = "in_progress"
        self.save()
        self._structured_log("INFO", step_name, f"Step {step_id} started", None)

    def mark_step_complete(self, step_id: int, step_name: str, exit_code: int = 0) -> None:
        """Record successful step completion."""
        if step_id not in self.state["steps"]:
            self.state["steps"][step_id] = {"name": step_name}

        step = self.state["steps"][step_id]
        start = _parse_iso_or_now(step.get("start_time"))
        end = datetime.now(timezone.utc)
        duration = (end - start).total_seconds()

        step["status"] = "completed"
        step["end_time"] = end.isoformat()
        step["duration_sec"] = round(duration, 2)
        step["exit_code"] = exit_code
        step["error"] = None
        self.save()
        self._structured_log("INFO", step_name, f"Step {step_id} completed ({duration:.2f}s)", exit_code)

    def mark_step_failed(self, step_id: int, step_name: str, exit_code: int, error: str) -> None:
        """Record step failure with error context."""
        if step_id not in self.state["steps"]:
            self.state["steps"][step_id] = {"name": step_name}

        step = self.state["steps"][step_id]
        start = _parse_iso_or_now(step.get("start_time"))
        end = datetime.now(timezone.utc)
        duration = (end - start).total_seconds()

        step["status"] = "failed"
        step["end_time"] = end.isoformat()
        step["duration_sec"] = round(duration, 2)
        step["exit_code"] = exit_code
        step["error"] = error

        self.state["overall_status"] = "failed"
        self.save()

        self._structured_log("ERROR", step_name, f"Step {step_id} failed: {error}", exit_code)

    def get_resume_point(self) -> Optional[int]:
        """Return the first failed step to resume from, or None if all completed."""
        for step_id in sorted(self.state["steps"].keys()):
            if self.state["steps"][step_id]["status"] != "completed":
                return step_id
        return None

    def get_completed_steps(self) -> List[int]:
        """Return list of completed step IDs."""
        return [
            step_id for step_id, step in self.state["steps"].items()
            if step.get("status") == "completed"
        ]

    def reset(self) -> None:
        """Completely reset checkpoint state."""
        self.state = self._create_empty_state()
        self.save()
        self._structured_log("INFO", "CHECKPOINT", "Pipeline checkpoint reset", 0)

    def report(self) -> str:
        """Generate human-readable checkpoint report."""
        lines = [
            "=" * 70,
            "PIPELINE CHECKPOINT REPORT",
            "=" * 70,
            f"Overall Status: {self.state['overall_status'].upper()}",
            f"Updated: {self.state.get('last_updated', 'unknown')}",
            "",
            "STEP STATUS:",
            "-" * 70,
        ]

        completed_count = 0
        failed_step = None
        total_duration = 0

        for step_id in sorted(self.state["steps"].keys()):
            step = self.state["steps"][step_id]
            status = step.get("status", "unknown").upper()
            duration = step.get("duration_sec", 0)
            total_duration += duration

            status_icon = {
                "COMPLETED": "✓",
                "RUNNING": "→",
                "FAILED": "✗",
                "PENDING": " "
            }.get(status, "?")

            error_msg = ""
            if step.get("error"):
                error_msg = f" | ERROR: {step['error'][:60]}"
                if not failed_step:
                    failed_step = step_id

            duration_str = f"{duration:.1f}s" if duration > 0 else "-"
            lines.append(
                f"  [{status_icon}] Step {step_id:2d}: {step.get('name', 'unknown'):<40} [{duration_str:>6}]{error_msg}"
            )

            if status == "COMPLETED":
                completed_count += 1

        lines.extend([
            "-" * 70,
            f"Completed: {completed_count}/{len(self.state['steps'])} steps",
            f"Total elapsed: {total_duration:.1f}s",
        ])

        if failed_step is not None:
            lines.append(f"Can resume from step {failed_step}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _structured_log(self, level: str, step: str, message: str, exit_code: Optional[int]) -> None:
        """Write structured log entry to JSON log file."""
        log_entry = {
            "timestamp": _utc_now_iso(),
            "level": level,
            "step": step,
            "message": message,
            "exit_code": exit_code
        }

        # Append to structured log
        if STRUCTURED_LOG.exists():
            logs = json.loads(STRUCTURED_LOG.read_text(encoding="utf-8"))
            if not isinstance(logs, list):
                logs = []
        else:
            logs = []

        logs.append(log_entry)
        STRUCTURED_LOG.write_text(json.dumps(logs, indent=2), encoding="utf-8")

    @staticmethod
    def _require_file(path: Path, minimum_bytes: int = 1) -> None:
        """Require that file exists and has at least minimum_bytes size."""
        if not path.exists() or not path.is_file():
            raise ValidationError(f"Missing expected output file: {path.relative_to(ROOT)}")
        if path.stat().st_size < minimum_bytes:
            raise ValidationError(
                f"Output file is too small ({path.stat().st_size} bytes): {path.relative_to(ROOT)}"
            )

    @staticmethod
    def _require_json(path: Path, required_keys: Optional[List[str]] = None) -> None:
        """Require that a JSON file exists, parses, and optionally has required keys."""
        PipelineCheckpoint._require_file(path, minimum_bytes=2)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as ex:
            raise ValidationError(f"Invalid JSON at {path.relative_to(ROOT)}: {ex}") from ex

        if required_keys:
            if not isinstance(payload, dict):
                raise ValidationError(f"Expected JSON object at {path.relative_to(ROOT)}")
            for key in required_keys:
                if key not in payload:
                    raise ValidationError(f"Missing key '{key}' in {path.relative_to(ROOT)}")

    def validate_step_output(self, step_id: int) -> None:
        """
        Validate key outputs after selected steps.

        Raises ValidationError on failures so the runner can mark the step failed.
        """
        if step_id == 7:
            # Align Lyrics To Audio
            self._require_file(ROOT / "02_INPUT" / "lyrics" / "lyrics_timed.srt")
            self._require_file(ROOT / "02_INPUT" / "lyrics" / "lyrics_timed.pre_offset.srt")
            return

        if step_id == 8:
            # Generate ASS Subtitles
            self._require_file(ROOT / "02_INPUT" / "lyrics" / "lyrics_styled.ass")
            self._require_file(ROOT / "02_INPUT" / "lyrics" / "lyrics_timed.srt")
            return

        if step_id == 10:
            # Build Sections
            self._require_json(ROOT / "03_WORK" / "sections" / "timeline.json", required_keys=["sections"])
            return

        if step_id == 13:
            # Build Timeline Manifest
            self._require_json(
                ROOT / "03_WORK" / "sections" / "timeline_manifest.json",
                required_keys=["sections"],
            )
            return

        if step_id == 14:
            # Render Master Video
            self._require_file(ROOT / "04_OUTPUT" / "youtube_16x9" / "master_clean.mp4", minimum_bytes=1024)
            return


def get_checkpoint() -> PipelineCheckpoint:
    """Convenience function to get/create checkpoint instance."""
    return PipelineCheckpoint()


if __name__ == "__main__":
    # CLI for testing/debugging
    if len(sys.argv) < 2:
        cp = get_checkpoint()
        print(cp.report())
    elif sys.argv[1] == "--reset":
        cp = get_checkpoint()
        cp.reset()
        print("Checkpoint reset.")
    elif sys.argv[1] == "--report":
        cp = get_checkpoint()
        print(cp.report())
