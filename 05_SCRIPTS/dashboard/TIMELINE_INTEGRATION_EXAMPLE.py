# Integration Example for Timeline Director
# Add this to your existing 05_SCRIPTS/dashboard/app.py

"""
Enhanced Flask backend for Timeline Director integration
Shows how to wire up the React component with Python pipeline utilities
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
from pathlib import Path
from datetime import datetime

# Import the timeline manager
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from timeline_manager import TimelineManager, TimelineConfig, TimelineTrack, TimelineClip

app = Flask(__name__)
CORS(app)

# ============================================================================
# TIMELINE DIRECTOR ENDPOINTS
# ============================================================================

@app.route('/api/timeline/save', methods=['POST'])
def save_timeline():
    """
    Save timeline configuration from the UI to 03_WORK/
    
    Expected JSON:
    {
        "duration": 120.0,
        "tracks": [
            {
                "id": "video-1",
                "type": "video",
                "clips": [
                    {
                        "id": "clip-1",
                        "name": "intro.mp4",
                        "start": 0,
                        "duration": 10,
                        "offset": 0
                    }
                ]
            }
        ]
    }
    """
    try:
        data = request.json
        
        # Convert request data to TimelineConfig
        tracks = []
        for track_data in data.get('tracks', []):
            clips = []
            for clip_data in track_data.get('clips', []):
                # Infer file path from name
                file_ext = os.path.splitext(clip_data['name'])[1]
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
            duration=data['duration'],
            tracks=tracks,
            created_at=datetime.now().isoformat()
        )
        
        # Save using timeline manager
        saved_path = TimelineManager.save_timeline(config)
        
        return jsonify({
            'status': 'success',
            'message': f'Timeline saved to {saved_path}',
            'path': saved_path
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@app.route('/api/timeline/load', methods=['GET'])
def load_timeline():
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
        
        return jsonify(timeline_data), 200
        
    except FileNotFoundError:
        return jsonify({
            'status': 'not_found',
            'message': 'No timeline configuration found'
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/timeline/validate', methods=['POST'])
def validate_timeline():
    """Validate the current timeline configuration"""
    try:
        data = request.json
        
        # Convert to TimelineConfig
        tracks = []
        for track_data in data.get('tracks', []):
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
            duration=data['duration'],
            tracks=tracks,
            created_at=datetime.now().isoformat()
        )
        
        # Run validation
        validation = TimelineManager.validate_timeline(config)
        
        return jsonify(validation), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'valid': False
        }), 400


@app.route('/api/timeline/export-render', methods=['POST'])
def export_for_rendering():
    """Export timeline in rendering-pipeline format"""
    try:
        data = request.json
        
        # Convert to TimelineConfig
        tracks = []
        for track_data in data.get('tracks', []):
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
            duration=data['duration'],
            tracks=tracks,
            created_at=datetime.now().isoformat()
        )
        
        render_spec = TimelineManager.export_for_rendering(config)
        
        return jsonify(render_spec), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@app.route('/api/timeline/report', methods=['GET'])
def get_timeline_report():
    """Get the latest timeline validation report"""
    try:
        config = TimelineManager.load_timeline()
        report_path = TimelineManager.generate_report(config)
        
        with open(report_path) as f:
            report = json.load(f)
        
        return jsonify(report), 200
        
    except FileNotFoundError:
        return jsonify({
            'message': 'No timeline configuration to report on'
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/timeline/checkpoint', methods=['POST'])
def checkpoint_timeline():
    """Save timeline to checkpoint for resumable pipeline"""
    try:
        from checkpoint_manager import CheckpointManager
        
        data = request.json
        timeline_data = {
            'duration': data.get('duration'),
            'tracks': data.get('tracks', [])
        }
        
        checkpoint = CheckpointManager.save_checkpoint('timeline', timeline_data)
        
        return jsonify({
            'status': 'success',
            'checkpoint': checkpoint
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# HELPER ENDPOINTS FOR FILE DISCOVERY
# ============================================================================

@app.route('/api/media/list-videos', methods=['GET'])
def list_videos():
    """List available video files in 02_INPUT/video/"""
    try:
        video_dir = Path('02_INPUT/video')
        video_files = []
        
        if video_dir.exists():
            video_extensions = {'.mp4', '.mov', '.mkv', '.avi', '.webm'}
            for file in video_dir.iterdir():
                if file.is_file() and file.suffix.lower() in video_extensions:
                    video_files.append({
                        'name': file.name,
                        'path': str(file),
                        'size': file.stat().st_size,
                        'modified': file.stat().st_mtime
                    })
        
        return jsonify(sorted(video_files, key=lambda x: x['name'])), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/media/list-audio', methods=['GET'])
def list_audio():
    """List available audio files in 02_INPUT/audio/"""
    try:
        audio_dir = Path('02_INPUT/audio')
        audio_files = []
        
        if audio_dir.exists():
            audio_extensions = {'.mp3', '.wav', '.aac', '.flac', '.m4a', '.wma'}
            for file in audio_dir.iterdir():
                if file.is_file() and file.suffix.lower() in audio_extensions:
                    audio_files.append({
                        'name': file.name,
                        'path': str(file),
                        'size': file.stat().st_size,
                        'modified': file.stat().st_mtime
                    })
        
        return jsonify(sorted(audio_files, key=lambda x: x['name'])), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# INTEGRATION WITH EXISTING DASHBOARD
# ============================================================================

@app.route('/timeline-editor')
def timeline_editor():
    """
    Serve the timeline editor page
    This route serves your React component
    """
    return render_template('timeline_editor.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
