from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Add core scripts to path for timeline manager import
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from timeline_manager import TimelineManager, TimelineConfig, TimelineTrack, TimelineClip

ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = ROOT / "03_WORK"
LOGS_DIR = WORK_DIR / "logs"
REPORTS_DIR = WORK_DIR / "reports"
ANALYSIS_DIR = WORK_DIR / "analysis"
OUTPUT_DIR = ROOT / "04_OUTPUT"
CONFIG_DIR = ROOT / "01_CONFIG"

CHECKPOINT_FILE = WORK_DIR / "pipeline_checkpoint.json"
STRUCTURED_LOG = LOGS_DIR / "pipeline_execution.json"
DELIVERY_MANIFEST = OUTPUT_DIR / "delivery_manifest.json"
EXPORT_PRESETS_FILE = CONFIG_DIR / "export_presets.json"
PIPELINE_RUNNER = ROOT / "05_SCRIPTS" / "run_release_pipeline_resumable.ps1"
RUNTIME_STATE_FILE = LOGS_DIR / "dashboard_runtime_state.json"

STATIC_DIR = Path(__file__).resolve().parent / "static"
RUNTIME_LOCK_TIMEOUT_SEC = 8 * 60 * 60
CONTROL_COOLDOWN_SEC = 2

@asynccontextmanager
async def _lifespan(_: FastAPI):
    _ensure_dirs()
    _refresh_runtime_state()
    yield


app = FastAPI(title="LJV Visual Engine Dashboard API", version="0.1.0", lifespan=_lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _safe_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        tmp.write(json.dumps(payload, indent=2))
        temp_name = tmp.name
    Path(temp_name).replace(path)


def _parse_iso8601(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    check_cmd = (
        "$process = Get-Process -Id "
        + str(pid)
        + " -ErrorAction SilentlyContinue; if ($process) { exit 0 } else { exit 1 }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", check_cmd],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    return result.returncode == 0


def _load_runtime_state() -> Dict[str, Any]:
    base = {
        "active": False,
        "pid": None,
        "mode": None,
        "started_at": None,
        "lock_expires_at": None,
        "last_action_at": None,
        "updated_at": _utc_now(),
        "last_exit_code": None,
        "last_action": None,
        "last_error": None,
    }
    state = _safe_read_json(RUNTIME_STATE_FILE, base)
    if not isinstance(state, dict):
        return base
    merged = base | state
    return merged


def _save_runtime_state(state: Dict[str, Any]) -> None:
    state["updated_at"] = _utc_now()
    _safe_write_json(RUNTIME_STATE_FILE, state)


def _checkpoint_payload() -> Dict[str, Any]:
    payload = _safe_read_json(CHECKPOINT_FILE, {})
    return payload if isinstance(payload, dict) else {}


def _has_failed_step(checkpoint: Dict[str, Any]) -> bool:
    steps = checkpoint.get("steps", {})
    if not isinstance(steps, dict):
        return False
    for step in steps.values():
        if isinstance(step, dict) and step.get("status") == "failed":
            return True
    return False


def _checkpoint_exit_code(checkpoint: Dict[str, Any]) -> int | None:
    overall = checkpoint.get("overall_status")
    if overall == "failed":
        return 1
    if overall == "completed":
        return 0
    return None


def _refresh_runtime_state() -> Dict[str, Any]:
    state = _load_runtime_state()
    pid = state.get("pid")
    checkpoint = _checkpoint_payload()

    lock_expiry = _parse_iso8601(state.get("lock_expires_at"))
    if state.get("active") and lock_expiry and datetime.now(timezone.utc) > lock_expiry:
        state["active"] = False
        state["last_error"] = "runtime_lock_expired"
        if state.get("last_exit_code") is None:
            state["last_exit_code"] = _checkpoint_exit_code(checkpoint)
        _save_runtime_state(state)
        return state

    if state.get("active") and isinstance(pid, int):
        if not _is_pid_running(pid):
            state["active"] = False
            if state.get("last_exit_code") is None:
                state["last_exit_code"] = _checkpoint_exit_code(checkpoint)
            _save_runtime_state(state)
    return state


def _checkpoint_summary(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    steps = checkpoint.get("steps", {}) if isinstance(checkpoint, dict) else {}
    if not isinstance(steps, dict):
        steps = {}

    normalized_steps: Dict[int, Dict[str, Any]] = {}
    for key, value in steps.items():
        try:
            step_id = int(key)
        except Exception:
            continue
        normalized_steps[step_id] = value if isinstance(value, dict) else {}

    total = len(normalized_steps)
    completed = sum(1 for s in normalized_steps.values() if s.get("status") == "completed")
    failed = sum(1 for s in normalized_steps.values() if s.get("status") == "failed")
    running_step = next(
        (
            {"id": sid, "name": step.get("name"), "started_at": step.get("start_time")}
            for sid, step in sorted(normalized_steps.items())
            if step.get("status") == "running"
        ),
        None,
    )
    progress_pct = round((completed / total) * 100, 2) if total else 0.0

    return {
        "overall_status": checkpoint.get("overall_status", "unknown"),
        "updated_at": checkpoint.get("last_updated"),
        "total_steps": total,
        "completed_steps": completed,
        "failed_steps": failed,
        "progress_pct": progress_pct,
        "running_step": running_step,
    }


def _build_reports_payload() -> Dict[str, Any]:
    preflight = _safe_read_json(REPORTS_DIR / "preflight_validation_report.json", {})
    quality = _safe_read_json(REPORTS_DIR / "quality_gate_report.json", {})
    readiness = _safe_read_json(REPORTS_DIR / "release_readiness_report.json", {})
    alignment = _safe_read_json(ANALYSIS_DIR / "lyrics_alignment_status.json", {})

    def summarize_status(report: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(report, dict):
            return {"status": "missing", "errors": 0, "warnings": 0}
        errors = report.get("errors", [])
        warnings = report.get("warnings", [])
        status = report.get("status", "unknown")
        return {
            "status": status,
            "errors": len(errors) if isinstance(errors, list) else 0,
            "warnings": len(warnings) if isinstance(warnings, list) else 0,
        }

    return {
        "preflight": {"summary": summarize_status(preflight), "raw": preflight},
        "quality_gate": {"summary": summarize_status(quality), "raw": quality},
        "release_readiness": {"summary": summarize_status(readiness), "raw": readiness},
        "alignment": {"raw": alignment},
    }


def _list_output_artifacts(limit: int = 200) -> Dict[str, Any]:
    manifest = _safe_read_json(DELIVERY_MANIFEST, {})
    files: List[Dict[str, Any]] = []

    for suffix in ("*.mp4", "*.json"):
        for path in OUTPUT_DIR.rglob(suffix):
            if len(files) >= limit:
                break
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                files.append(
                    {
                        "path": rel,
                        "size_bytes": path.stat().st_size,
                        "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                    }
                )

    files.sort(key=lambda item: item["modified_at"], reverse=True)
    return {"manifest": manifest, "files": files[:limit]}


def _artifact_group_for_path(path: str) -> str:
    normalized = path.lower()
    known_prefixes = [
        "04_output/youtube_16x9/",
        "04_output/vertical_9x16/",
        "04_output/square_1x1/",
        "04_output/teasers/",
        "04_output/clean_visualizer/",
        "04_output/lyric_visualizer/",
        "04_output/promo_cards/",
        "04_output/release_bundle/",
    ]
    for prefix in known_prefixes:
        if normalized.startswith(prefix):
            return prefix.split("/")[1]
    return "other"


def _resolve_workspace_path(path: str) -> Path:
    candidate = (ROOT / path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


def _download_url_for_path(path: str) -> str:
    return f"/api/files/download?path={quote(path, safe='/._-')}"


def _build_artifact_browser(limit: int = 200) -> Dict[str, Any]:
    payload = _list_output_artifacts(limit=limit)
    files = payload.get("files", [])
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    latest_video: Dict[str, Any] | None = None

    for item in files:
        file_path = str(item.get("path", ""))
        group = _artifact_group_for_path(file_path)
        entry = {
            "path": file_path,
            "size_bytes": item.get("size_bytes", 0),
            "modified_at": item.get("modified_at"),
            "is_video": file_path.lower().endswith(".mp4"),
            "download_url": _download_url_for_path(file_path),
        }
        grouped.setdefault(group, []).append(entry)
        if entry["is_video"] and latest_video is None:
            latest_video = entry

    for group_entries in grouped.values():
        group_entries.sort(key=lambda x: str(x.get("modified_at", "")), reverse=True)

    return {
        "groups": grouped,
        "latest_video": latest_video,
        "manifest": payload.get("manifest", {}),
    }


def _build_layout_summary() -> Dict[str, Any]:
    presets = _safe_read_json(EXPORT_PRESETS_FILE, {})
    presets_by_target = presets.get("targets", {}) if isinstance(presets, dict) else {}
    output_targets = {
        "youtube_16x9": OUTPUT_DIR / "youtube_16x9",
        "vertical_9x16": OUTPUT_DIR / "vertical_9x16",
        "square_1x1": OUTPUT_DIR / "square_1x1",
        "teasers": OUTPUT_DIR / "teasers",
    }

    layouts: List[Dict[str, Any]] = []
    for target, folder in output_targets.items():
        target_cfg = presets_by_target.get(target, {}) if isinstance(presets_by_target, dict) else {}
        width = target_cfg.get("width") if isinstance(target_cfg, dict) else None
        height = target_cfg.get("height") if isinstance(target_cfg, dict) else None
        fps = target_cfg.get("fps") if isinstance(target_cfg, dict) else None
        video_count = len(list(folder.glob("*.mp4"))) if folder.exists() else 0

        layouts.append(
            {
                "target": target,
                "dimensions": f"{width}x{height}" if width and height else "unknown",
                "fps": fps if fps is not None else "unknown",
                "videos": video_count,
                "folder": folder.relative_to(ROOT).as_posix(),
            }
        )

    return {"layouts": layouts}


def _start_pipeline(mode: str) -> Dict[str, Any]:
    if not PIPELINE_RUNNER.exists():
        raise HTTPException(status_code=500, detail="Pipeline runner script is missing")

    valid_modes = {"start", "resume", "retry", "force"}
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Unsupported control mode: {mode}")

    state = _refresh_runtime_state()
    if state.get("active"):
        raise HTTPException(status_code=409, detail="A pipeline run is already active")

    last_action_at = _parse_iso8601(state.get("last_action_at"))
    if last_action_at and (datetime.now(timezone.utc) - last_action_at).total_seconds() < CONTROL_COOLDOWN_SEC:
        raise HTTPException(status_code=429, detail="Control action cooldown active. Try again shortly.")

    checkpoint = _checkpoint_payload()
    if mode == "retry" and not _has_failed_step(checkpoint):
        raise HTTPException(status_code=409, detail="Retry is only available when checkpoint has a failed step")

    args = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(PIPELINE_RUNNER),
    ]

    if mode in {"resume", "retry"}:
        args.append("-Resume")
    elif mode == "force":
        args.append("-Force")

    process = subprocess.Popen(
        args,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    new_state = {
        "active": True,
        "pid": process.pid,
        "mode": mode,
        "started_at": _utc_now(),
        "lock_expires_at": (datetime.now(timezone.utc) + timedelta(seconds=RUNTIME_LOCK_TIMEOUT_SEC)).isoformat(),
        "last_action_at": _utc_now(),
        "updated_at": _utc_now(),
        "last_exit_code": None,
        "last_action": f"start:{mode}",
        "last_error": None,
    }
    _save_runtime_state(new_state)
    return new_state


@app.get("/")
def dashboard_root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> Dict[str, Any]:
    state = _refresh_runtime_state()
    return {
        "status": "ok",
        "time": _utc_now(),
        "active_run": state.get("active", False),
    }


@app.get("/api/state")
def state() -> Dict[str, Any]:
    runtime = _refresh_runtime_state()
    checkpoint = _checkpoint_payload()
    summary = _checkpoint_summary(checkpoint if isinstance(checkpoint, dict) else {})
    has_failed_step = _has_failed_step(checkpoint)
    return {
        "runtime": runtime,
        "checkpoint": summary,
        "controls": {
            "can_start": not runtime.get("active", False),
            "can_resume": not runtime.get("active", False),
            "can_retry": (not runtime.get("active", False)) and has_failed_step,
            "has_failed_step": has_failed_step,
        },
    }


@app.get("/api/checkpoint")
def checkpoint() -> Dict[str, Any]:
    payload = _checkpoint_payload()
    if not payload:
        return {"exists": False, "checkpoint": {}, "summary": _checkpoint_summary({})}
    return {
        "exists": True,
        "checkpoint": payload,
        "summary": _checkpoint_summary(payload if isinstance(payload, dict) else {}),
    }


@app.get("/api/logs")
def logs(
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=2000),
) -> Dict[str, Any]:
    entries = _safe_read_json(STRUCTURED_LOG, [])
    if not isinstance(entries, list):
        entries = []

    safe_cursor = min(cursor, len(entries))
    end = min(safe_cursor + limit, len(entries))
    batch = entries[safe_cursor:end]

    return {
        "cursor": safe_cursor,
        "next_cursor": end,
        "total": len(entries),
        "entries": batch,
    }


@app.get("/api/reports")
def reports() -> Dict[str, Any]:
    return _build_reports_payload()


@app.get("/api/artifacts")
def artifacts(limit: int = Query(default=120, ge=1, le=1000)) -> Dict[str, Any]:
    return _list_output_artifacts(limit=limit)


@app.get("/api/artifact-browser")
def artifact_browser(limit: int = Query(default=120, ge=1, le=1000)) -> Dict[str, Any]:
    return _build_artifact_browser(limit=limit)


@app.get("/api/layouts")
def layouts() -> Dict[str, Any]:
    return _build_layout_summary()


@app.get("/api/preview/default")
def preview_default() -> Dict[str, Any]:
    payload = _build_artifact_browser(limit=240)
    latest_video = payload.get("latest_video")
    if latest_video is None:
        return {"exists": False, "video": None}
    video_path = latest_video.get("path")
    return {
        "exists": True,
        "video": {
            "path": video_path,
            "download_url": _download_url_for_path(str(video_path)),
            "modified_at": latest_video.get("modified_at"),
            "size_bytes": latest_video.get("size_bytes", 0),
        },
    }


@app.get("/api/files/download")
def file_download(path: str = Query(..., min_length=1)) -> FileResponse:
    file_path = _resolve_workspace_path(path)
    return FileResponse(file_path, filename=file_path.name)


@app.post("/api/control/start")
def control_start() -> Dict[str, Any]:
    return {"runtime": _start_pipeline("start")}


@app.post("/api/control/resume")
def control_resume() -> Dict[str, Any]:
    return {"runtime": _start_pipeline("resume")}


@app.post("/api/control/retry")
def control_retry() -> Dict[str, Any]:
    return {"runtime": _start_pipeline("retry")}


@app.post("/api/control/force")
def control_force() -> Dict[str, Any]:
    return {"runtime": _start_pipeline("force")}


# ============================================================================
# TIMELINE DIRECTOR ENDPOINTS
# ============================================================================

@app.post("/api/timeline/save")
def save_timeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save timeline configuration from the UI to 03_WORK/
    
    Expected payload:
    {
        "duration": 120.0,
        "tracks": [
            {
                "id": "video-1",
                "type": "video",
                "clips": [...]
            }
        ]
    }
    """
    try:
        # Convert request data to TimelineConfig
        tracks = []
        for track_data in payload.get('tracks', []):
            clips = []
            for clip_data in track_data.get('clips', []):
                # Infer file path from name and type
                if track_data['type'] == 'video':
                    file_path = f"02_INPUT/video/{clip_data['name']}"
                else:
                    file_path = f"02_INPUT/audio/{clip_data['name']}"
                
                clip = TimelineClip(
                    id=clip_data['id'],
                    name=clip_data['name'],
                    file_path=file_path,
                    start_time=clip_data['start'],
                    duration=clip_data['duration'],
                    offset=clip_data.get('offset', 0)
                )
                clips.append(clip)
            
            track = TimelineTrack(
                id=track_data['id'],
                track_type=track_data['type'],
                clips=clips
            )
            tracks.append(track)
        
        config = TimelineConfig(
            duration=payload['duration'],
            tracks=tracks,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Save using timeline manager
        saved_path = TimelineManager.save_timeline(config)
        
        return {
            'status': 'success',
            'message': f'Timeline saved',
            'path': str(saved_path)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/timeline/load")
def load_timeline() -> Dict[str, Any]:
    """Load existing timeline configuration"""
    try:
        config = TimelineManager.load_timeline()
        
        # Convert back to JSON-serializable format
        timeline_data = {
            'duration': config.duration,
            'tracks': [
                {
                    'id': track.id,
                    'type': track.track_type,
                    'visible': track.visible,
                    'solo': track.solo,
                    'locked': track.locked,
                    'clips': [
                        {
                            'id': clip.id,
                            'name': clip.name,
                            'start': clip.start_time,
                            'duration': clip.duration,
                            'offset': clip.offset
                        }
                        for clip in track.clips
                    ]
                }
                for track in config.tracks
            ]
        }
        
        return timeline_data
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='No timeline configuration found')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/timeline/validate")
def validate_timeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the current timeline configuration"""
    try:
        # Convert to TimelineConfig
        tracks = []
        for track_data in payload.get('tracks', []):
            clips = [
                TimelineClip(
                    id=c['id'],
                    name=c['name'],
                    file_path=f"02_INPUT/{track_data['type']}/{c['name']}",
                    start_time=c['start'],
                    duration=c['duration'],
                    offset=c.get('offset', 0)
                )
                for c in track_data.get('clips', [])
            ]
            
            tracks.append(TimelineTrack(
                id=track_data['id'],
                track_type=track_data['type'],
                clips=clips
            ))
        
        config = TimelineConfig(
            duration=payload['duration'],
            tracks=tracks,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Run validation
        return TimelineManager.validate_timeline(config)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/timeline/export-render")
def export_for_rendering(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Export timeline in rendering-pipeline format"""
    try:
        # Convert to TimelineConfig
        tracks = []
        for track_data in payload.get('tracks', []):
            clips = [
                TimelineClip(
                    id=c['id'],
                    name=c['name'],
                    file_path=f"02_INPUT/{track_data['type']}/{c['name']}",
                    start_time=c['start'],
                    duration=c['duration'],
                    offset=c.get('offset', 0)
                )
                for c in track_data.get('clips', [])
            ]
            
            tracks.append(TimelineTrack(
                id=track_data['id'],
                track_type=track_data['type'],
                clips=clips
            ))
        
        config = TimelineConfig(
            duration=payload['duration'],
            tracks=tracks,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        return TimelineManager.export_for_rendering(config)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/timeline/report")
def get_timeline_report() -> Dict[str, Any]:
    """Get the latest timeline validation report"""
    try:
        config = TimelineManager.load_timeline()
        report_path = TimelineManager.generate_report(config)
        
        with open(report_path) as f:
            report = json.load(f)
        
        return report
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='No timeline configuration to report on')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/media/list-videos")
def list_videos() -> Dict[str, Any]:
    """List available video files in 02_INPUT/video/"""
    try:
        video_dir = ROOT / "02_INPUT" / "video"
        video_files = []
        
        if video_dir.exists():
            video_extensions = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v'}
            for file in video_dir.iterdir():
                if file.is_file() and file.suffix.lower() in video_extensions:
                    video_files.append({
                        'name': file.name,
                        'path': str(file.relative_to(ROOT)),
                        'size': file.stat().st_size,
                        'modified': file.stat().st_mtime
                    })
        
        return {'videos': sorted(video_files, key=lambda x: x['name'])}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/media/list-audio")
def list_audio() -> Dict[str, Any]:
    """List available audio files in 02_INPUT/audio/"""
    try:
        audio_dir = ROOT / "02_INPUT" / "audio"
        audio_files = []
        
        if audio_dir.exists():
            audio_extensions = {'.mp3', '.wav', '.aac', '.flac', '.m4a', '.wma', '.opus'}
            for file in audio_dir.iterdir():
                if file.is_file() and file.suffix.lower() in audio_extensions:
                    audio_files.append({
                        'name': file.name,
                        'path': str(file.relative_to(ROOT)),
                        'size': file.stat().st_size,
                        'modified': file.stat().st_mtime
                    })
        
        return {'audio': sorted(audio_files, key=lambda x: x['name'])}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/timeline-editor")
def timeline_editor() -> FileResponse:
    """Serve the timeline editor page"""
    timeline_html = Path(__file__).resolve().parent / "static" / "timeline_editor.html"
    return FileResponse(timeline_html)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LJV dashboard API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)
