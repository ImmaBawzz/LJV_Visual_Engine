# Timeline Director Integration - Testing Checklist

**Project**: LJV Visual Engine  
**Component**: Timeline Director  
**Date**: March 31, 2026  
**Tester**: [Your Name]  

---

## Pre-Test Setup

- [ ] Python environment configured  
- [ ] FastAPI and Uvicorn installed (`pip install fastapi uvicorn`)
- [ ] Sample media files prepared (or using existing media)
- [ ] Dashboard starts without errors:  
  `cd 05_SCRIPTS/dashboard` then `..\..\.venv\Scripts\python.exe app.py --host 127.0.0.1 --port 8787`
- [ ] Timeline editor loads at http://localhost:8787/timeline-editor
- [ ] If you see JSON `{"detail":"Not Found"}` at `/timeline-editor`, stop old servers and restart from `05_SCRIPTS/dashboard`

---

## Feature Testing

### 1. UI & Layout
- [ ] Page loads with dark theme applied
- [ ] Header displays: "🎬 Timeline Director"
- [ ] Sidebar visible with track controls
- [ ] Timeline area shows empty state: "👈 Add a track to get started"
- [ ] Bottom-right inspector panel area visible
- [ ] All controls responsive and accessible

### 2. Track Management
- [ ] [+ Video] button creates orange-bordered video track
- [ ] [+ Audio] button creates purple-bordered audio track
- [ ] Multiple tracks can be added (test 3-5 tracks)
- [ ] Each track shows correct icon (🎥 or 🎵)
- [ ] Track header displays track ID

### 3. Media Import
- [ ] Drop zone visible on empty tracks
- [ ] Can drag video files onto video track
- [ ] Can drag audio files onto audio track
- [ ] File picker works when clicking drop zone
- [ ] Clips appear at position 0s with default 5s duration
- [ ] Clip name displays correctly
- [ ] Importing multiple files creates multiple clips

### 4. Clip Positioning
- [ ] Can drag clips left/right on timeline
- [ ] Playhead updates Red line during drag
- [ ] Clips snap to approximate positions
- [ ] Clip position reflects in timeline ruler
- [ ] Dragging to 0s works correctly
- [ ] Dragging past timeline duration is prevented

### 5. Timeline Display
- [ ] Ruler shows time markers (0s, 5s, 10s, etc.)
- [ ] Ruler updates when duration changes
- [ ] Ruler marks are clearly visible
- [ ] Scrolling horizontally works on timeline
- [ ] Timeline displays clips correctly colored:
  - Video clips: warm brown/orange colors
  - Audio clips: purple colors

### 6. Playback Controls
- [ ] "▶ Play" button starts playback
- [ ] Playhead moves smoothly across timeline
- [ ] "⏸ Pause" button stops playback
- [ ] "⏮ Reset" button returns playhead to 0s
- [ ] Playhead slider can be dragged
- [ ] Clicking timeline jumps playhead to that position
- [ ] Timecode displays current/total time

### 7. Inspector Panel
- [ ] Clicking clip selects it (blue border)
- [ ] Inspector opens with clip properties
- [ ] Inspector shows clip name
- [ ] Inspector shows current start time
- [ ] Inspector shows duration (read-only)
- [ ] Inspector shows offset value
- [ ] Can edit start time in inspector
- [ ] Can edit offset time in inspector
- [ ] Changes immediately reflect on timeline
- [ ] "🗑 Delete Clip" button removes clip

### 8. Zoom Functionality
- [ ] "🔍+ Zoom" button enlarges timeline (1.0x → 1.2x)
- [ ] Can zoom multiple times (up to 3.0x)
- [ ] "🔍- Unzoom" button shrinks timeline
- [ ] Can unzoom down to 0.5x
- [ ] Clips scale proportionally with zoom
- [ ] Timeline positioning preserved during zoom

### 9. Track Controls
- [ ] 👁 (visibility) button toggles track opacity
- [ ] Hidden tracks display at 50% opacity
- [ ] Can show/hide multiple tracks independently
- [ ] S (solo) button highlights track with cyan border
- [ ] Only one track can be soloed at once
- [ ] Solo button can be toggled off
- [ ] 🔒 (lock) button disables dragging
- [ ] Locked tracks show visual indicator
- [ ] Locked clips can't be moved

### 10. Settings Panel
- [ ] Duration input shows current value
- [ ] Can change duration to different values
- [ ] Duration changes reflect on ruler
- [ ] New clips respect the new timeline duration

### 11. Features (Pipeline Section)
- [ ] "💾 Save Config" button visible
- [ ] "📂 Load Config" button visible
- [ ] "✓ Validate" button visible
- [ ] Message display shows feedback

### 12. Save Functionality
- [ ] Clicking "💾 Save Config" sends request to server
- [ ] Success message: "✅ Timeline saved to pipeline"
- [ ] File created: `03_WORK/timeline_config.json`
- [ ] File contains valid JSON
- [ ] JSON includes all tracks and clips
- [ ] JSON includes correct timing values
- [ ] Backup created: `03_WORK/backups/timeline_config.backup.json`

### 13. Load Functionality
- [ ] Clicking "📂 Load Config" loads previous timeline
- [ ] All clips are restored to correct positions
- [ ] All track properties are preserved
- [ ] Duration matches saved value
- [ ] Message confirms successful load
- [ ] Missing file shows appropriate message

### 14. Validation
- [ ] Clicking "✓ Validate" runs validation
- [ ] Validation panel appears (bottom-right)
- [ ] Shows status (✅ VALID or ❌ INVALID)
- [ ] Lists error count
- [ ] Lists warning count
- [ ] Shows summary: clips count, track count
- [ ] Errors appear with red background
- [ ] Warnings appear with orange background
- [ ] Can close validation panel

### 15. Responsive Behavior
- [ ] Inspector hides on smaller screens (<1200px width)
- [ ] Sidebar resizes appropriately
- [ ] Zoom controls always visible
- [ ] Main timeline remains usable on all screen sizes

---

## API Testing

### Backend Endpoints

- [ ] GET `/api/timeline/load` returns 404 when no config exists
- [ ] POST `/api/timeline/save` creates config file
- [ ] POST `/api/timeline/save` validates payload
- [ ] GET `/api/timeline/load` returns saved config
- [ ] POST `/api/timeline/validate` checks timing
- [ ] POST `/api/timeline/validate` detects overlaps
- [ ] POST `/api/timeline/export-render` returns render spec
- [ ] GET `/api/timeline/report` returns validation report
- [ ] GET `/api/media/list-videos` returns video files
- [ ] GET `/api/media/list-audio` returns audio files

### Data Integrity

- [ ] Saved config JSON is valid and parseable
- [ ] All clip properties preserved through save/load cycle
- [ ] Timing values accurate to 2 decimal places
- [ ] Track order preserved
- [ ] Clip order preserved

---

## Error Handling

- [ ] Empty timeline can be saved (0 clips)
- [ ] Missing media files show in validation warnings
- [ ] Clips extending beyond duration show error
- [ ] Overlapping audio tracks show warning (if applicable)
- [ ] Network errors handled gracefully
- [ ] Invalid JSON rejected with clear error

---

## Performance & Stability

- [ ] No lag when dragging clips
- [ ] Playback smooth at all zoom levels
- [ ] Handles 10+ clips without slowdown
- [ ] Handles 5+ tracks without slowdown
- [ ] No memory leaks visible in extended testing
- [ ] Page survives multiple save/load cycles

---

## Browser Compatibility

**Tested Browsers:**
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Edge
- [ ] Safari (if on Mac)

**Per Browser:**
- [ ] All controls functional
- [ ] No console errors
- [ ] No styling issues
- [ ] Drag-and-drop works

---

## Integration Tests

- [ ] Python backend starts without .errors
- [ ] Python imports timeline_manager successfully
- [ ] FastAPI serves HTML without errors
- [ ] React CDN loads successfully
- [ ] No CORS errors in console
- [ ] File I/O works correctly

---

## Documentation & Code Quality

- [ ] Code is readable and well-commented
- [ ] Error messages are user-friendly
- [ ] API endpoints match documentation
- [ ] Configuration format matches specification
- [ ] File paths are correct for project structure

---

## Ready for Production?

- [ ] All critical features working
- [ ] No major bugs found
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] Code follows project conventions

---

## Issues Found

If any tests fail, document them here:

### Issue 1
- **Test**: [Which test failed]
- **Expected**: [What should happen]
- **Actual**: [What actually happened]
- **Steps to Reproduce**: [How to reproduce]
- **Severity**: [Critical/Major/Minor]

### Issue 2
[Same format]

---

## Sign-Off

**Tested By**: ________________  
**Date**: ________________  
**Status**: ☐ PASS ☐ FAIL ☐ CONDITIONAL  

**Notes**: _______________________________________________

---

## Ready to Push to GitHub?

Once all tests pass (or issues are documented and accepted):

```powershell
git add -A
git commit -m "feat: integrate Timeline Director for media import and timing

- Add FastAPI endpoints for timeline management
- Create timeline editor with React UI
- Support save/load/validate workflows
- Export configurations for rendering pipeline"

git push origin main
```

**Repository**: ImmaBawzz/LJV_Visual_Engine  
**Branch**: main  
**Status**: Ready for merge ✅
