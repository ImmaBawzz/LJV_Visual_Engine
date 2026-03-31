# 🎬 Timeline Director - Complete Design & Implementation Guide

## Overview

**Timeline Director** is a professional-grade timeline and media import interface designed specifically for the LJV Visual Engine directing workflow. It bridges the gap between creative direction (visual/audio import and positioning) and the automated rendering pipeline.

Think of it as:
- **For Directors**: A visual tool to arrange music, audio, and video clips in precise timing
- **For the Pipeline**: A configuration generator that feeds into `03_WORK/` stages
- **For Collaboration**: A checkpoint-compatible state that can resume at any time

---

## Design Philosophy

### 1. **Inspired by Industry Standards**
- **DaVinci Resolve** UI language for familiarity
- Professional dark theme with color-coded tracks
- Precise time controls matching broadcast standards
- Non-destructive workflows (always exportable)

### 2. **Focused on Directing**
Unlike full video editors, Timeline Director is streamlined for:
- ✅ Import and position media clips
- ✅ Set exact timing and sync points
- ✅ Manage multiple tracks (video + audio)
- ✅ Real-time preview and playback
- ✅ Export for pipeline processing

Not included (intentionally):
- ❌ Complex effects/transitions
- ❌ Color grading
- ❌ Rendering (delegated to pipeline)
- ❌ Advanced compositing

### 3. **Pipeline Integration**
```
Timeline Director UI → timeline_config.json → Pipeline (rendering/processing)
                                           ↓
                                    03_WORK/timeline/
                                    quality gate reports
                                    render specifications
```

---

## Architecture

### Frontend: React Component
```
TimelineDirector (container)
├── Header (transport controls, playhead slider, timecode)
├── Sidebar (track controls, tools, project settings)
├── Timeline (ruler, tracks, clips, playhead)
│   ├── Timeline Ruler (time markers)
│   ├── Track (video/audio)
│   │   ├── Track Header (metadata, controls)
│   │   └── Track Content (clips, drop zone)
│   │       ├── TimelineClip (draggable)
│   │       └── TimelineClip
│   └── Playhead (red indicator)
└── Inspector Panel (clip properties, editing)
```

### Backend: Python Utilities
```
timeline_manager.py
├── TimelineClip (dataclass)
├── TimelineTrack (dataclass)
├── TimelineConfig (dataclass)
└── TimelineManager (IO, validation, export)
    ├── save_timeline() → 03_WORK/timeline_config.json
    ├── load_timeline() ← 03_WORK/timeline_config.json
    ├── validate_timeline() → validation report
    ├── generate_report() → quality gate data
    └── export_for_rendering() → render specification
```

### Flask Backend Integration
```
Flask (app.py additions)
├── /api/timeline/save ← UI configuration
├── /api/timeline/load → resumable state
├── /api/timeline/validate → quality checks
├── /api/timeline/export-render → pipeline format
├── /api/timeline/checkpoint → resumable checkpoint
└── /api/media/list-* → available files
```

---

## User Workflow

### Step 1: Start Timeline
```
Click "+ Video" and "+ Audio" in sidebar
→ Creates empty tracks ready for content
```

### Step 2: Import Media
```
Drag files onto tracks OR click drop zone
→ Files added to 02_INPUT/{type}/ location
→ Clips appear on timeline at position 0
```

### Step 3: Position Clips
```
Drag clips left/right to desired start time
OR use Inspector panel for frame-accurate positioning
→ Real-time visual feedback
```

### Step 4: Fine-tune Timing
```
Click clip → Inspector panel opens
Adjust:
  - Start time (when clip begins on timeline)
  - Duration (how long clip plays)
  - Offset (where to start within source file)
→ Useful for: trimming, delaying audio sync, etc.
```

### Step 5: Preview
```
Click Play button
→ Red playhead moves through timeline
→ Scrub with slider for frame-accurate navigation
→ See exactly how clips align
```

### Step 6: Export & Process
```
Click "Save to Pipeline" 
→ Configuration saved to 03_WORK/timeline_config.json
→ Quality validation report generated
→ Ready for rendering stages (09_build_sections.py, etc.)
```

### Step 7: Checkpoint (Optional)
```
Can pause work at any time
Timeline saves to checkpoint system
Resume later with exact state preserved
→ Integrates with resumable pipeline (05_SCRIPTS/core/checkpoint_manager.py)
```

---

## Configuration Format

The Timeline Director outputs a standardized JSON format:

```json
{
  "version": "1.0",
  "created_at": "2026-03-31T15:30:00",
  "duration": 120.0,
  "tracks": [
    {
      "id": "video-1700000000000",
      "type": "video",
      "visible": true,
      "solo": false,
      "locked": false,
      "clips": [
        {
          "id": "video-1700000000000-clip-1700000000000",
          "name": "intro.mp4",
          "file_path": "02_INPUT/video/intro.mp4",
          "start_time": 0.0,
          "duration": 5.0,
          "offset": 0.0,
          "end_time": 5.0
        },
        {
          "id": "video-1700000000000-clip-1700000000001",
          "name": "main.mp4",
          "file_path": "02_INPUT/video/main.mp4",
          "start_time": 5.0,
          "duration": 115.0,
          "offset": 2.5,
          "end_time": 120.0
        }
      ]
    },
    {
      "id": "audio-1700000000000",
      "type": "audio",
      "visible": true,
      "solo": false,
      "locked": false,
      "clips": [
        {
          "id": "audio-1700000000000-clip-1700000000000",
          "name": "music.wav",
          "file_path": "02_INPUT/audio/music.wav",
          "start_time": 1.0,
          "duration": 119.0,
          "offset": 0.0,
          "end_time": 120.0
        }
      ]
    }
  ]
}
```

---

## Control Reference

### Transport Controls (Header)
| Control | Shortcut | Effect |
|---------|----------|--------|
| Play/Pause | Space* | Toggle playback |
| Reset | ⏮ | Jump to 0s |
| Playhead Slider | Drag | Scrub to any frame |

### Track Controls (Header)
| Button | Effect |
|--------|--------|
| 👁 | Toggle visibility (fade out in preview) |
| S | Solo (only this track audible in play) |
| 🔒 | Lock (prevent accidental movement) |

### Sidebar Tools
| Tool | Effect |
|------|--------|
| Zoom + / - | Scale timeline (0.5x to 3.0x) |
| 📍 Markers | Show/hide beat/marker indicators |
| Duration | Set total timeline length |

### Clip Operations
| Action | Effect |
|--------|--------|
| Drag | Move clip along timeline |
| Click | Select for inspector editing |
| Inspector Start | Set exact start frame |
| Inspector Offset | Start from frame N in source |
| Delete | Remove clip from timeline |

---

## Validation & Quality Checks

The `TimelineManager.validate_timeline()` performs:

✅ **Timing Checks**
- Clips don't extend beyond timeline duration
- Start times are non-negative
- Duration values are valid

⚠️ **Warnings**
- Missing source files  
- Audio track overlaps (might cause mixing issues)
- Unused tracks

❌ **Errors**
- Critical timing violations
- File not found
- Track configuration issues

Example validation output:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "File not found: 02_INPUT/video/missing.mp4"
  ],
  "timeline_duration": 120.0,
  "total_clips": 3,
  "audio_tracks": 1,
  "video_tracks": 1
}
```

---

## Integration Points

### With Existing Scripts

```python
# In any 05_SCRIPTS/core/*.py processing script:

from timeline_manager import TimelineManager

# Load the configuration
timeline = TimelineManager.load_timeline()

# Use in your processing
for track in timeline.tracks:
    if track.track_type == 'video':
        for clip in track.clips:
            print(f"Process {clip.name} from {clip.start_time}s to {clip.start_time + clip.duration}s")
```

### With Checkpoint System

```python
# In checkpoint_manager.py, add timeline support:

CHECKPOINT_STAGES = {
    # ... existing stages ...
    'timeline': {
        'description': 'Timeline Director configuration',
        'file': '03_WORK/timeline_config.json',
        'required_inputs': [],
        'outputs': ['timeline_config.json']
    }
}
```

### With Quality Gates

```python
# In quality_gate_report.py:

timeline_report = TimelineManager.generate_report(timeline_config)
quality_gates = {
    'timeline_valid': timeline_report['validation']['valid'],
    'clip_count': timeline_report['timeline_summary']['total_clips'],
    'duration_match': timeline_config.duration == expected_duration
}
```

---

## Performance Considerations

### Recommended Limits
- **Tracks**: Up to 20 per project (UI performance)
- **Clips**: Up to 100 total (responsive dragging)
- **Timeline Length**: Up to 600s (10 minutes) at normal zoom

### Optimization Tips
- **Zoom In** for precise edit work
- **Hide inactive tracks** to reduce render overhead
- **Lock tracks** you're not editing
- **Solo tracks** to focus on specific content

### For Large Projects
- Split into segments: intro (0-30s), main (30-90s), outro (90-120s)
- Work on segments separately, then stitch configs together
- Use checkpoints to save progress frequently

---

## Extending Timeline Director

### Add Beat Detection
```jsx
const detectBeats = (audioFile) => {
  // Use Web Audio API or send to backend for analysis
  // Return array of beat times
  return [0.5, 1.0, 1.5, 2.0, ...];
};

// Add as visual markers:
const [markers, setMarkers] = useState(detectBeats(audioClip));
```

### Add Waveform Visualization
```jsx
// Replace clip header with waveform canvas
<canvas
  ref={waveformRef}
  width={width}
  height={60}
  onLoad={() => drawWaveform(clip.file)}
/>
```

### Add Trim/Split Tools
```jsx
const getTrimPoints = (clipId) => {
  // Returns in/out points for trimming
};

const splitClip = (clipId, atTime) => {
  // Creates two clips from one
};
```

### Add Effects/Transitions
```jsx
const applyEffect = (clipId, effect) => {
  // 'fade-in', 'fade-out', 'dissolve', etc.
  // Store in clip metadata
};
```

---

## Troubleshooting

### Files Won't Import
- ✅ Check file extension (video/* or audio/*)
- ✅ Verify files exist in 02_INPUT/
- ✅ Try drag-and-drop vs. file picker

### Timeline Won't Save
- ✅ Check write permissions on 03_WORK/
- ✅ Ensure 03_WORK/ directory exists
- ✅ Check JSON formatting in validation

### Clips Skip During Playback
- ✅ Reduce timeline zoom level
- ✅ Close other applications (memory pressure)
- ✅ Check browser performance (DevTools → Performance)

### Audio/Video Out of Sync
- ✅ Adjust **Offset** values in inspector
- ✅ Use **Markers** to align to beat
- ✅ Enable **Solo** to hear individual tracks

---

## File Structure Reference

```
LJV_Visual_Engine_RELEASE_Package/
├── 02_INPUT/
│   ├── audio/      ← Drop audio files here
│   ├── video/      ← Drop video files here
│   ├── branding/
│   ├── images/
│   ├── lyrics/
│   ├── metadata/
│   └── ...
├── 03_WORK/
│   ├── timeline_config.json        ← Timeline Director output 🎯
│   ├── backups/
│   │   └── timeline_config.backup.json
│   ├── reports/
│   │   └── timeline_report.json    ← Validation & analysis
│   └── ... (other processing stages)
├── 05_SCRIPTS/
│   ├── core/
│   │   ├── timeline_manager.py     ← Python utilities
│   │   ├── checkpoint_manager.py   ← Resumable state
│   │   └── ...
│   └── dashboard/
│       ├── components/
│       │   ├── TimelineDirector.jsx    ← React component
│       │   ├── TimelineDirector.css    ← Styling
│       │   └── README_TimelineDirector.md
│       └── app.py                      ← Flask backend
├── 09_DOCS/
│   └── CHECKPOINT_GUIDE.md         ← Pipeline integration
└── ...
```

---

## API Reference

### React Component

```jsx
import TimelineDirector from './components/TimelineDirector';

<TimelineDirector />
```

No props required - works standalone.

### Python Backend

```python
from timeline_manager import TimelineManager, TimelineConfig

# Save
TimelineManager.save_timeline(config)

# Load
timeline = TimelineManager.load_timeline()

# Validate
report = TimelineManager.validate_timeline(config)

# Generate report
path = TimelineManager.generate_report(config)

# Export for rendering
render_spec = TimelineManager.export_for_rendering(config)
```

### Flask API

```
POST /api/timeline/save           → Save from UI
GET  /api/timeline/load           → Resume work
POST /api/timeline/validate       → Check quality
POST /api/timeline/export-render  → Get render instructions
GET  /api/timeline/report         → Latest validation
POST /api/timeline/checkpoint     → Save resumable state
```

---

## Future Roadmap

### Phase 2
- [ ] Beat/BPM detection
- [ ] Audio waveform visualization  
- [ ] Clip trim/split tools
- [ ] Fade in/out effects
- [ ] Jump cuts / section markers

### Phase 3
- [ ] Real-time audio monitoring
- [ ] Video preview with thumbnails
- [ ] Undo/redo stack
- [ ] Keyboard shortcuts
- [ ] Multi-language support

### Phase 4
- [ ] Collaborative editing (WebSocket sync)
- [ ] Version history with git integration
- [ ] Export to different formats
- [ ] Template/preset system
- [ ] AI-powered suggestions (beat sync, auto-trim)

---

## Support & Documentation

- 📖 **Component README**: [README_TimelineDirector.md](./README_TimelineDirector.md)
- 🐍 **Python Module**: [timeline_manager.py](../core/timeline_manager.py)
- 🔧 **Integration Example**: [TIMELINE_INTEGRATION_EXAMPLE.py](./TIMELINE_INTEGRATION_EXAMPLE.py)
- 📋 **Pipeline Guide**: [CHECKPOINT_GUIDE.md](../../09_DOCS/CHECKPOINT_GUIDE.md)
- 🎥 **Project Docs**: [09_DOCS/](../../09_DOCS/)

---

**Created**: March 31, 2026  
**Status**: Ready for Integration  
**Next Step**: Add to dashboard and test with sample media
