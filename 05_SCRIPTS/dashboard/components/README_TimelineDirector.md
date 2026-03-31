# 🎬 Timeline Director - Integration Guide

A professional timeline-based media import and director interface for your LJV Visual Engine, inspired by DaVinci Resolve but streamlined for directing workflows.

## Features

### Core Timeline Controls
- **Multi-track timeline** - Add unlimited video and audio tracks
- **Drag-and-drop clips** - Drag media directly onto tracks or import via file picker
- **Precise positioning** - Frame-accurate clip placement with time display
- **Real-time playback** - Play through your timeline with visual playhead
- **Zoom controls** - Zoom in/out for detailed editing or full-view overview

### Track Management
- **Track visibility** - Toggle track visibility (👁 button)
- **Solo tracks** - Isolate individual tracks for focus
- **Lock tracks** - Prevent accidental modifications
- **Type-coded tracks** - Video tracks (🎥) and Audio tracks (🎵) distinguished by color

### Clip Inspector
- **Property editor** - Fine-tune clip start times, duration, and offset
- **Real-time sync** - Changes immediately reflected in timeline
- **Bulk operations** - Delete clips or batch-modify properties

### Visual Design
- Dark professional theme matching DaVinci Resolve
- Color-coded tracks (cyan for general, orange for video, purple for audio)
- Professional typography and subtle animations
- Responsive layout that works on different screen sizes

## Installation

### 1. Add to Your React Dashboard

```jsx
import TimelineDirector from './components/TimelineDirector';

function App() {
  return (
    <div className="app">
      <TimelineDirector />
      {/* Your other components */}
    </div>
  );
}

export default App;
```

### 2. With CSS Import

Make sure your build system handles CSS imports:

```jsx
import TimelineDirector from './components/TimelineDirector';
import './components/TimelineDirector.css';
```

### 3. In a Container Component

```jsx
import React, { useState } from 'react';
import TimelineDirector from './components/TimelineDirector';

export function EditorTab() {
  return (
    <div style={{ height: '600px' }}>
      <TimelineDirector />
    </div>
  );
}
```

## Integration with Your Pipeline

### Connecting to 03_WORK/ Data

After building your timeline, export the configuration to feed into your pipeline:

```python
# 05_SCRIPTS/core/export_timeline_config.py
import json
from datetime import datetime

def export_timeline_to_pipeline(timeline_config):
    """
    Converts Timeline Director configuration into pipeline-compatible format
    for use with checkpoint_manager.py and subsequent processing stages.
    """
    
    export = {
        "export_timestamp": datetime.now().isoformat(),
        "timeline_duration": timeline_config['duration'],
        "tracks": []
    }
    
    for track in timeline_config['tracks']:
        track_data = {
            "id": track['id'],
            "type": track['type'],  # 'video' or 'audio'
            "clips": [
                {
                    "name": clip['name'],
                    "file_path": f"02_INPUT/{track['type']}/{clip['name']}",
                    "start_time": clip['start'],
                    "duration": clip['duration'],
                    "offset": clip['offset'],
                    "timeline_position": clip['start'],
                    "end_time": clip['start'] + clip['duration']
                }
                for clip in track['clips']
            ]
        }
        export['tracks'].append(track_data)
    
    # Save to work directory
    output_path = "03_WORK/timeline_config.json"
    with open(output_path, 'w') as f:
        json.dump(export, f, indent=2)
    
    return output_path
```

### Reading Timeline Configuration in Python

```python
# Use in your existing pipeline scripts
import json

def load_timeline_config():
    with open("03_WORK/timeline_config.json") as f:
        return json.load(f)

timeline = load_timeline_config()
for track in timeline['tracks']:
    for clip in track['clips']:
        print(f"{clip['name']}: {clip['start_time']}s - {clip['end_time']}s")
```

## API Reference

### Component Props

The `TimelineDirector` component doesn't require any props - it's fully self-contained:

```jsx
<TimelineDirector />
```

But you can extend it to accept callbacks:

```jsx
<TimelineDirector 
  onTimelineChange={(config) => console.log(config)}
  defaultDuration={120}
/>
```

### Internal State Management

The component manages these states internally:

```javascript
{
  tracks: [
    {
      id: string,
      type: 'video' | 'audio',
      clips: [
        {
          id: string,
          name: string,
          start: number,        // seconds
          duration: number,      // seconds
          offset: number,        // seconds
          file: File
        }
      ],
      visible: boolean,
      solo: boolean,
      locked: boolean,
      volume: number,           // 0-100
      opacity: number           // 0-100
    }
  ],
  playhead: number,             // current position in seconds
  duration: number,              // total timeline duration
  isPlaying: boolean,
  selectedClip: object,
  zoom: number                  // 0.5 to 3.0
}
```

## Keyboard Shortcuts (To Add)

Future enhancement - consider adding:

```javascript
// Proposed keyboard shortcuts
const SHORTCUTS = {
  'Space': 'togglePlayback',
  'Delete': 'deleteSelectedClip',
  'A': 'addAudioTrack',
  'V': 'addVideoTrack',
  'Ctrl+Z': 'undo',
  'Ctrl+Y': 'redo'
};
```

## Extending the Component

### Add Markers/Beats

```jsx
const [markers, setMarkers] = useState([]);

const addMarker = (time, label) => {
  setMarkers([...markers, { time, label, id: Date.now() }]);
};
```

### Add Effects/Transitions

```jsx
const [clipEffects, setClipEffects] = useState({});

const applyEffect = (clipId, effectType) => {
  // 'fade', 'slide', 'dissolve', etc.
};
```

### Export Timeline to Video Format

```jsx
const exportTimeline = async () => {
  const config = { tracks, duration, zoom };
  const response = await fetch('/api/render-timeline', {
    method: 'POST',
    body: JSON.stringify(config)
  });
  // Handle rendering response
};
```

## Usage Workflow

1. **Create Tracks**: Click "+ Video" or "+ Audio" in the sidebar
2. **Import Media**: Drag files directly onto tracks or click the drop zone
3. **Position Clips**: Drag clips left/right on the timeline
4. **Fine-tune**: Click a clip to open the inspector panel and adjust timing
5. **Preview**: Click the Play button to preview your timeline
6. **Export**: Use the export function to save to `03_WORK/` for pipeline processing

## Styling Customization

The component uses CSS custom properties where possible. To customize colors:

```css
.timeline-director {
  --color-primary: #00d9ff;
  --color-accent-video: #ff9d5e;
  --color-accent-audio: #7b5af2;
  --color-danger: #ff6b6b;
  --bg-primary: #1a1a1a;
  --bg-secondary: #0d0d0d;
}
```

## Performance Notes

- Optimized for up to 20 tracks with reasonable responsive performance
- Drag operations use refs to minimize re-renders
- Consider virtual scrolling for projects with 50+ clips

## Browser Support

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- IE11: Not supported (uses modern CSS Grid, Flexbox)

## Troubleshooting

### Clips not dragging smoothly
- Check browser devtools for performance issues
- Zoom level may affect responsiveness

### Timeline not syncing with audio
- Ensure audio codec is supported by browser
- Check file format compatibility

### Files not importing
- Verify file is in correct format (video/* or audio/*)
- Check browser permissions for file access

## Future Enhancements

- [ ] Audio waveform visualization
- [ ] Beat/marker detection
- [ ] Trim/split clip tools
- [ ] Transition effects
- [ ] Color grading presets
- [ ] Collaboration features
- [ ] Real-time rendering preview
- [ ] Export to different formats
- [ ] Undo/redo stack
- [ ] Keyboard shortcuts

## License

Part of LJV Visual Engine - See LICENSE file

---

For questions or feature requests, refer to the main project documentation in `09_DOCS/`.
