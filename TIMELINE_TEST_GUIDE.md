# Timeline Director Integration - Quick Test Guide

## Overview
This guide walks you through testing the Timeline Director integration with your LJV Visual Engine dashboard.

## What's Been Integrated

✅ **FastAPI Endpoints** in `05_SCRIPTS/dashboard/app.py`:
- POST `/api/timeline/save` - Save timeline config
- GET `/api/timeline/load` - Load existing config
- POST `/api/timeline/validate` - Validate timing/sync
- POST `/api/timeline/export-render` - Export for rendering
- GET `/api/timeline/report` - Get validation report
- GET `/api/media/list-videos` - List available videos
- GET `/api/media/list-audio` - List available audio
- GET `/timeline-editor` - Serve Timeline Editor page

✅ **Timeline Editor Page** in `05_SCRIPTS/dashboard/static/`:
- `timeline_editor.html` - Main UI page
- `timeline_director.js` - React component (bundled)
- `timeline_director.css` - Professional styling

✅ **Python Backend** in `05_SCRIPTS/core/`:
- `timeline_manager.py` - Configuration management, validation, export

## Pre-Test Setup

### 1. Prepare Sample Media (Optional)
Run the setup script to create sample video/audio files:

```powershell
cd c:\Users\Shadow\Downloads\LJV_Visual_Engine_RELEASE_Package
python 05_SCRIPTS\setup_timeline_test.py
```

This will:
- Create directories: `02_INPUT/video/` and `02_INPUT/audio/`
- Generate sample media files (if ffmpeg is installed) OR
- Create placeholder markers for you to add your own files

### 2. Start the Dashboard
Open PowerShell and run:

```powershell
cd c:\Users\Shadow\Downloads\LJV_Visual_Engine_RELEASE_Package
python 05_SCRIPTS\dashboard\app.py --host 127.0.0.1 --port 8787
```

You should see:
```
INFO:     Started server process [XXXX]
INFO:     Uvicorn running on http://127.0.0.1:8787
```

### 3. Open Timeline Editor
In your browser, navigate to:
```
http://localhost:8787/timeline-editor
```

You should see the Timeline Director UI with:
- Dark professional theme
- Sidebar with track controls
- Empty timeline ready for content

## Testing Workflow

### Test 1: Create Tracks and Add Media

1. **Add Tracks**
   - Click `+ Video` in sidebar (creates orange-bordered video track)
   - Click `+ Audio` in sidebar (creates purple-bordered audio track)

2. **Import Media**
   - Option A: Drag & drop video files onto video track
   - Option B: Click drop zone to browse for files
   - Same for audio track

Expected: Clips appear at 0s with default 5s duration

### Test 2: Position Clips on Timeline

1. **Drag Clips**
   - Click and drag a clip left/right to reposition
   - Watch timeline playhead update in real-time
   - Try dragging to different positions (5s, 15s, 30s, etc.)

2. **Use Inspector**
   - Click any clip to open inspector panel (right side)
   - Modify "Start" time directly
   - Watch clip move on timeline
   - Try different offset values (delays within the source file)

Expected: Clips move smoothly, timing displays update, no errors

### Test 3: Playback Preview

1. **Play Timeline**
   - Click `▶ Play` button
   - Red playhead should move across timeline
   - Timeline should loop back when reaching duration

2. **Scrub Timeline**
   - Drag the slider or click any point on ruler
   - Playhead should jump to that position

Expected: Playback works smoothly, no freezing

### Test 4: Zoom & Navigation

1. **Zoom In**
   - Click `🔍+ Zoom` button a few times
   - Timeline should expand (more space per second)
   - Can see more detail in clip positions

2. **Zoom Out**
   - Click `🔍- Unzoom` to contract
   - See overview of entire timeline

Expected: Zoom changes timeline scale without losing data

### Test 5: Track Controls

1. **Visibility Toggle**
   - Click 👁 icon on track header
   - Track should fade/become visible

2. **Solo**
   - Click `S` button on one track
   - Only that track shows active (cyan highlight)
   - Click again to deselect

3. **Lock**
   - Click 🔒 button on a track
   - Try dragging clips in that track (should not move)
   - Click again to unlock

Expected: All controls work without errors

### Test 6: Validation

1. **Validate Timeline**
   - Click `✓ Validate` button in sidebar
   - Validation panel appears (bottom-right)
   - Should show status (✅ VALID or ❌ INVALID)

2. **Check Results**
   - Shows number of clips, video/audio tracks
   - Lists any errors or warnings
   - Close button to dismiss

Expected: Validation runs correctly

### Test 7: Save & Load Configuration

1. **Save Configuration**
   - Set up a timeline with several clips
   - Click `💾 Save Config`
   - Should show: "✅ Timeline saved to pipeline"
   - Config saved to: `03_WORK/timeline_config.json`

2. **Load Configuration**
   - Refresh page or close editor
   - Click `📂 Load Config`
   - Should restore previous timeline layout
   - All clips, positions, durations preserved

Expected: Round-trip save/load works perfectly

## Verification Checklist

After testing, verify these files were created:

```
03_WORK/
├── timeline_config.json          ← Configuration file
├── backups/
│   └── timeline_config.backup.json
└── reports/
    └── timeline_report.json      ← Validation report
```

Check `03_WORK/timeline_config.json` content (should be valid JSON):

```json
{
  "version": "1.0",
  "created_at": "2026-03-31T...",
  "duration": 120.0,
  "tracks": [
    {
      "id": "video-...",
      "type": "video",
      "visible": true,
      "clips": [...]
    }
  ]
}
```

## Troubleshooting

### Dashboard won't start
**Problem**: `ModuleNotFoundError: No module named 'fastapi'`
**Solution**: Install dependencies
```powershell
pip install fastapi uvicorn
```

### Can't find timeline module
**Problem**: `ModuleNotFoundError: No module named 'timeline_manager'`
**Solution**: Make sure `05_SCRIPTS/core/timeline_manager.py` exists and has correct permissions

### Browser blank page or React not loading
**Problem**: Timeline page shows blank or errors in console
**Solution**: 
- Check browser console (F12) for errors
- Verify `static/timeline_director.js` and `.css` exist
- Clear browser cache (Ctrl+Shift+Del)

### Can't drag clips
**Problem**: Clips won't move when dragging
**Solution**:
- Make sure track isn't locked (check 🔒 button)
- Try different clip
- Check browser console for JavaScript errors

### Save button doesn't work
**Problem**: "❌ Error saving timeline" message
**Solution**:
- Check if `03_WORK/` directory exists and is writable
- Verify `core/timeline_manager.py` is in correct location
- Check backend logs for errors

## Next Steps After Testing

Once you've verified everything works:

### 1. Commit Changes to GitHub
```powershell
cd c:\Users\Shadow\Downloads\LJV_Visual_Engine_RELEASE_Package
git add -A
git commit -m "feat: integrate Timeline Director for media import and timing control

- Add FastAPI endpoints for timeline CRUD operations
- Create dedicated timeline editor UI with React
- Integrate timeline_manager for configuration persistence
- Support save/load/validate workflows
- Export configurations to pipeline format"

git push origin main
```

### 2. Integration with Your Pipeline
To use Timeline Director output in your rendering pipeline:

```python
# In 05_SCRIPTS/core/09_build_sections.py (example)
from timeline_manager import TimelineManager

# Load timeline configuration
timeline = TimelineManager.load_timeline()

# Use in section building
for track in timeline.tracks:
    if track.track_type == 'video':
        for clip in track.clips:
            process_video_segment(
                clip.file_path,
                start=clip.start_time,
                duration=clip.duration,
                offset=clip.offset
            )
```

### 3. Add to Checkpoint System (Optional)
Integrate with existing resumable pipeline:

```python
# In checkpoint_manager.py, add stage:
{
    'timeline': {
        'description': 'Timeline Director configuration',
        'required_inputs': [],
        'outputs': ['timeline_config.json']
    }
}
```

## Features Available Now

✅ Create video and audio tracks  
✅ Import media via drag-drop  
✅ Position clips with frame accuracy  
✅ Real-time timeline preview  
✅ Track visibility, solo, lock controls  
✅ Save/load configurations  
✅ Validate timing and sync  
✅ Export for rendering pipeline  
✅ Professional DaVinci Resolve-inspired UI  

## Future Enhancements (Not in This Release)

- Audio waveform visualization
- Beat/BPM detection and markers
- Clip trimming and splitting tools
- Fade in/out and transitions
- Keyboard shortcuts
- Undo/redo history
- Real-time rendering preview

---

**Ready to push to GitHub?**

Once all tests pass, commit and push your changes:
```powershell
git push origin main
```

Your Timeline Director integration is now live! 🎉
