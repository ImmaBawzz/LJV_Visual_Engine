"""
Timeline Director Configuration Handler
Integrates with LJV Visual Engine pipeline checkpoint system

This module provides utilities to:
1. Load/save timeline configurations from the UI
2. Convert timeline data to pipeline-compatible format
3. Validate timing and sync issues
4. Generate reports for the quality gate
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class TimelineClip:
    """Represents a single clip on the timeline"""
    id: str
    name: str
    file_path: str
    start_time: float  # seconds
    duration: float  # seconds
    offset: float  # seconds


@dataclass
class TimelineTrack:
    """Represents a single track in the timeline"""
    id: str
    track_type: str  # 'video' or 'audio'
    clips: List[TimelineClip]
    visible: bool = True
    solo: bool = False
    locked: bool = False


@dataclass
class TimelineConfig:
    """Complete timeline configuration"""
    duration: float
    tracks: List[TimelineTrack]
    created_at: str
    export_version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.export_version,
            "created_at": self.created_at,
            "duration": self.duration,
            "tracks": [
                {
                    "id": track.id,
                    "type": track.track_type,
                    "visible": track.visible,
                    "solo": track.solo,
                    "locked": track.locked,
                    "clips": [
                        {
                            "id": clip.id,
                            "name": clip.name,
                            "file_path": clip.file_path,
                            "start_time": clip.start_time,
                            "duration": clip.duration,
                            "offset": clip.offset,
                            "end_time": clip.start_time + clip.duration,
                        }
                        for clip in track.clips
                    ]
                }
                for track in self.tracks
            ]
        }


class TimelineManager:
    """Manages timeline configuration IO and pipeline integration"""
    
    TIMELINE_CONFIG_PATH = "03_WORK/timeline_config.json"
    TIMELINE_BACKUP_PATH = "03_WORK/backups/timeline_config.backup.json"
    TIMELINE_REPORT_PATH = "03_WORK/reports/timeline_report.json"
    
    @staticmethod
    def ensure_directories():
        """Create necessary directories if they don't exist"""
        Path("03_WORK/backups").mkdir(parents=True, exist_ok=True)
        Path("03_WORK/reports").mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def save_timeline(cls, config: TimelineConfig) -> str:
        """
        Save timeline configuration to work directory
        
        Args:
            config: TimelineConfig object
            
        Returns:
            Path to saved configuration
        """
        cls.ensure_directories()
        
        # Create backup
        if os.path.exists(cls.TIMELINE_CONFIG_PATH):
            os.makedirs(os.path.dirname(cls.TIMELINE_BACKUP_PATH), exist_ok=True)
            with open(cls.TIMELINE_CONFIG_PATH) as src:
                with open(cls.TIMELINE_BACKUP_PATH, 'w') as dst:
                    dst.write(src.read())
        
        # Save new config
        with open(cls.TIMELINE_CONFIG_PATH, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        return cls.TIMELINE_CONFIG_PATH
    
    @classmethod
    def load_timeline(cls) -> TimelineConfig:
        """
        Load timeline configuration from work directory
        
        Returns:
            TimelineConfig object
            
        Raises:
            FileNotFoundError: If timeline config doesn't exist
        """
        if not os.path.exists(cls.TIMELINE_CONFIG_PATH):
            raise FileNotFoundError(f"Timeline config not found at {cls.TIMELINE_CONFIG_PATH}")
        
        with open(cls.TIMELINE_CONFIG_PATH) as f:
            data = json.load(f)
        
        tracks = []
        for track_data in data.get('tracks', []):
            clips = [
                TimelineClip(
                    id=clip['id'],
                    name=clip['name'],
                    file_path=clip['file_path'],
                    start_time=clip['start_time'],
                    duration=clip['duration'],
                    offset=clip['offset']
                )
                for clip in track_data.get('clips', [])
            ]
            
            tracks.append(TimelineTrack(
                id=track_data['id'],
                track_type=track_data['type'],
                clips=clips,
                visible=track_data.get('visible', True),
                solo=track_data.get('solo', False),
                locked=track_data.get('locked', False),
            ))
        
        return TimelineConfig(
            duration=data['duration'],
            tracks=tracks,
            created_at=data['created_at'],
            export_version=data.get('version', '1.0')
        )
    
    @classmethod
    def validate_timeline(cls, config: TimelineConfig) -> Dict[str, Any]:
        """
        Validate timeline configuration for pipeline compatibility
        
        Checks for:
        - Clips extending beyond timeline duration
        - Overlapping audio tracks
        - Missing files
        - Timing issues
        
        Returns:
            Validation report dictionary
        """
        report = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "timeline_duration": config.duration,
            "total_clips": sum(len(t.clips) for t in config.tracks),
            "audio_tracks": sum(1 for t in config.tracks if t.track_type == 'audio'),
            "video_tracks": sum(1 for t in config.tracks if t.track_type == 'video'),
        }
        
        # Check clip timing
        for track in config.tracks:
            for clip in track.clips:
                if clip.start_time + clip.duration > config.duration:
                    report["errors"].append(
                        f"Clip '{clip.name}' in {track.track_type} track "
                        f"extends beyond timeline ({clip.start_time + clip.duration}s > {config.duration}s)"
                    )
                    report["valid"] = False
                
                # Check if file exists
                if not os.path.exists(clip.file_path):
                    report["warnings"].append(
                        f"File not found: {clip.file_path}"
                    )
        
        # Check for overlapping audio
        audio_tracks = [t for t in config.tracks if t.track_type == 'audio']
        if len(audio_tracks) > 1:
            for i, track1 in enumerate(audio_tracks):
                for track2 in audio_tracks[i+1:]:
                    overlaps = cls._check_track_overlap(track1, track2)
                    if overlaps:
                        report["warnings"].append(
                            f"Audio overlap detected between {track1.id} and {track2.id}: {overlaps}"
                        )
        
        return report
    
    @staticmethod
    def _check_track_overlap(track1: TimelineTrack, track2: TimelineTrack) -> List[str]:
        """Check if clips overlap in time"""
        overlaps = []
        for clip1 in track1.clips:
            for clip2 in track2.clips:
                if not (clip1.start_time + clip1.duration <= clip2.start_time or 
                        clip2.start_time + clip2.duration <= clip1.start_time):
                    overlaps.append(
                        f"{clip1.name} ({clip1.start_time}-{clip1.start_time + clip1.duration}s) "
                        f"overlaps {clip2.name} ({clip2.start_time}-{clip2.start_time + clip2.duration}s)"
                    )
        return overlaps
    
    @classmethod
    def generate_report(cls, config: TimelineConfig) -> str:
        """
        Generate a comprehensive timeline report for quality gates
        
        Returns:
            Path to generated report
        """
        cls.ensure_directories()
        
        validation = cls.validate_timeline(config)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "validation": validation,
            "timeline_summary": {
                "duration": config.duration,
                "total_clips": validation["total_clips"],
                "audio_tracks": validation["audio_tracks"],
                "video_tracks": validation["video_tracks"],
            },
            "clips_detail": [
                {
                    "name": clip.name,
                    "type": track.track_type,
                    "start": clip.start_time,
                    "end": clip.start_time + clip.duration,
                    "duration": clip.duration,
                    "offset": clip.offset,
                }
                for track in config.tracks
                for clip in track.clips
            ]
        }
        
        with open(cls.TIMELINE_REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=2)
        
        return cls.TIMELINE_REPORT_PATH
    
    @classmethod
    def export_for_rendering(cls, config: TimelineConfig) -> Dict[str, Any]:
        """
        Export timeline data in format suitable for rendering pipeline
        
        Returns:
            Dictionary with rendering instructions
        """
        render_spec = {
            "timeline": {
                "duration": config.duration,
                "fps": 30,  # Adjust based on project
                "resolution": {
                    "width": 1920,
                    "height": 1080,
                    "fps": 30
                }
            },
            "video_tracks": [
                {
                    "track_id": track.id,
                    "clips": [
                        {
                            "source": clip.file_path,
                            "timeline_in": clip.start_time,
                            "timeline_out": clip.start_time + clip.duration,
                            "source_offset": clip.offset,
                            "opacity": 100 if track.visible else 0,
                        }
                        for clip in track.clips
                    ]
                }
                for track in config.tracks
                if track.track_type == 'video'
            ],
            "audio_tracks": [
                {
                    "track_id": track.id,
                    "clips": [
                        {
                            "source": clip.file_path,
                            "timeline_in": clip.start_time,
                            "timeline_out": clip.start_time + clip.duration,
                            "source_offset": clip.offset,
                            "volume": 100 if track.visible else 0,
                            "solo": track.solo,
                        }
                        for clip in track.clips
                    ]
                }
                for track in config.tracks
                if track.track_type == 'audio'
            ],
        }
        
        return render_spec


# Example usage
if __name__ == "__main__":
    # Create a sample timeline
    sample_config = TimelineConfig(
        duration=120.0,
        tracks=[
            TimelineTrack(
                id="video-1",
                track_type="video",
                clips=[
                    TimelineClip(
                        id="clip-1",
                        name="intro.mp4",
                        file_path="02_INPUT/video/intro.mp4",
                        start_time=0.0,
                        duration=10.0,
                        offset=0.0
                    ),
                    TimelineClip(
                        id="clip-2",
                        name="main.mp4",
                        file_path="02_INPUT/video/main.mp4",
                        start_time=10.0,
                        duration=100.0,
                        offset=5.0  # Start 5 seconds into the source
                    ),
                ]
            ),
            TimelineTrack(
                id="audio-1",
                track_type="audio",
                clips=[
                    TimelineClip(
                        id="audio-clip-1",
                        name="music.wav",
                        file_path="02_INPUT/audio/music.wav",
                        start_time=2.0,
                        duration=118.0,
                        offset=0.0
                    ),
                ]
            ),
        ],
        created_at=datetime.now().isoformat()
    )
    
    # Save configuration
    saved_path = TimelineManager.save_timeline(sample_config)
    print(f"✅ Timeline saved to: {saved_path}")
    
    # Validate
    validation = TimelineManager.validate_timeline(sample_config)
    print(f"\n📋 Validation: {'✅ VALID' if validation['valid'] else '❌ INVALID'}")
    if validation['errors']:
        for error in validation['errors']:
            print(f"  ❌ {error}")
    if validation['warnings']:
        for warning in validation['warnings']:
            print(f"  ⚠️  {warning}")
    
    # Generate report
    report_path = TimelineManager.generate_report(sample_config)
    print(f"\n📊 Report generated: {report_path}")
    
    # Export for rendering
    render_spec = TimelineManager.export_for_rendering(sample_config)
    print(f"\n🎬 Render specification generated with {len(render_spec['video_tracks'])} video + {len(render_spec['audio_tracks'])} audio tracks")
