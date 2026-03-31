// Timeline Director - React Component
// Bundled version for CDN-based React

const { useState, useRef, useEffect } = React;

const TimelineDirector = () => {
  const [tracks, setTracks] = useState([]);
  const [playhead, setPlayhead] = useState(0);
  const [duration, setDuration] = useState(120);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedClip, setSelectedClip] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [showMarkers, setShowMarkers] = useState(true);
  const [saveMessage, setSaveMessage] = useState('');
  const [validationResult, setValidationResult] = useState(null);
  const timelineRef = useRef(null);
  const playbackRef = useRef(null);

  // Add new track
  const addTrack = (type) => {
    const newTrack = {
      id: `${type}-${Date.now()}`,
      type,
      clips: [],
      visible: true,
      solo: false,
      locked: false,
      volume: 100,
      opacity: 100,
    };
    setTracks([...tracks, newTrack]);
  };

  // Load timeline from backend
  const loadTimeline = async () => {
    try {
      const response = await fetch('/api/timeline/load');
      if (response.ok) {
        const data = await response.json();
        setDuration(data.duration);
        
        // Convert loaded data back to track format
        const loadedTracks = data.tracks.map(t => ({
          id: t.id,
          type: t.type,
          clips: t.clips,
          visible: t.visible !== undefined ? t.visible : true,
          solo: t.solo || false,
          locked: t.locked || false,
          volume: 100,
          opacity: 100,
        }));
        setTracks(loadedTracks);
        setSaveMessage('✅ Timeline loaded successfully');
        
        // Clear message after 3 seconds
        setTimeout(() => setSaveMessage(''), 3000);
      } else {
        setSaveMessage('ℹ️ No existing timeline to load');
        setTimeout(() => setSaveMessage(''), 3000);
      }
    } catch (error) {
      setSaveMessage('❌ Error loading timeline: ' + error.message);
      setTimeout(() => setSaveMessage(''), 3000);
    }
  };

  // Save timeline to backend
  const saveTimeline = async () => {
    try {
      const payload = {
        duration,
        tracks: tracks.map(t => ({
          id: t.id,
          type: t.type,
          visible: t.visible,
          solo: t.solo,
          locked: t.locked,
          clips: t.clips
        }))
      };

      const response = await fetch('/api/timeline/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const result = await response.json();
        setSaveMessage('✅ Timeline saved to pipeline');
        setTimeout(() => setSaveMessage(''), 3000);
      } else {
        setSaveMessage('❌ Error saving timeline');
        setTimeout(() => setSaveMessage(''), 3000);
      }
    } catch (error) {
      setSaveMessage('❌ Network error: ' + error.message);
      setTimeout(() => setSaveMessage(''), 3000);
    }
  };

  // Validate timeline
  const validateTimeline = async () => {
    try {
      const payload = {
        duration,
        tracks: tracks.map(t => ({
          id: t.id,
          type: t.type,
          clips: t.clips
        }))
      };

      const response = await fetch('/api/timeline/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const result = await response.json();
        setValidationResult(result);
      }
    } catch (error) {
      console.error('Validation error:', error);
    }
  };

  // Handle file import
  const handleFileImport = (trackId, files) => {
    Array.from(files).forEach((file) => {
      const clip = {
        id: `${trackId}-clip-${Date.now()}`,
        name: file.name,
        start: 0,
        duration: 5,
        offset: 0,
        file: file,
      };

      setTracks(
        tracks.map((t) =>
          t.id === trackId ? { ...t, clips: [...t.clips, clip] } : t
        )
      );
    });
  };

  // Update clip position
  const updateClipPosition = (trackId, clipId, newStart) => {
    setTracks(
      tracks.map((track) =>
        track.id === trackId
          ? {
              ...track,
              clips: track.clips.map((clip) =>
                clip.id === clipId ? { ...clip, start: Math.max(0, newStart) } : clip
              ),
            }
          : track
      )
    );
  };

  // Toggle track visibility
  const toggleTrackVisibility = (trackId) => {
    setTracks(
      tracks.map((t) =>
        t.id === trackId ? { ...t, visible: !t.visible } : t
      )
    );
  };

  // Playback controls
  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  // Handle timeline click
  const handleTimelineClick = (e) => {
    if (!timelineRef.current) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const clickedTime = (x / rect.width) * duration;
    setPlayhead(Math.max(0, Math.min(duration, clickedTime)));
  };

  // Playback simulation
  useEffect(() => {
    let interval;
    if (isPlaying) {
      interval = setInterval(() => {
        setPlayhead((prev) => {
          if (prev >= duration) {
            setIsPlaying(false);
            return duration;
          }
          return prev + 0.016;
        });
      }, 16);
    }
    return () => clearInterval(interval);
  }, [isPlaying, duration]);

  const pixelsPerSecond = 50 * zoom;

  return (
    <div className="timeline-director">
      {/* Header */}
      <div className="director-header">
        <h2>🎬 Timeline Director</h2>
        <div className="transport-controls">
          <button onClick={togglePlayback} className="control-btn play-btn">
            {isPlaying ? '⏸ Pause' : '▶ Play'}
          </button>
          <button onClick={() => setPlayhead(0)} className="control-btn">
            ⏮ Reset
          </button>
          <input
            type="range"
            min="0"
            max={duration}
            step="0.1"
            value={playhead}
            onChange={(e) => setPlayhead(parseFloat(e.target.value))}
            className="playhead-slider"
          />
          <span className="timecode">
            {playhead.toFixed(2)}s / {duration.toFixed(2)}s
          </span>
        </div>
      </div>

      <div className="director-container">
        {/* Sidebar */}
        <div className="track-controls-sidebar">
          <div className="add-track-section">
            <h3>Tracks</h3>
            <button onClick={() => addTrack('video')} className="add-track-btn video-btn">
              + Video
            </button>
            <button onClick={() => addTrack('audio')} className="add-track-btn audio-btn">
              + Audio
            </button>
          </div>

          <div className="tools-section">
            <h3>Tools</h3>
            <button
              onClick={() => setZoom(Math.min(3, zoom + 0.2))}
              className="tool-btn"
            >
              🔍+ Zoom
            </button>
            <button
              onClick={() => setZoom(Math.max(0.5, zoom - 0.2))}
              className="tool-btn"
            >
              🔍- Unzoom
            </button>
            <button
              onClick={() => setShowMarkers(!showMarkers)}
              className={`tool-btn ${showMarkers ? 'active' : ''}`}
            >
              📍 Markers
            </button>
          </div>

          <div className="project-section">
            <h3>Project</h3>
            <label className="duration-label">
              Duration (s):
              <input
                type="number"
                value={duration}
                onChange={(e) => setDuration(parseFloat(e.target.value))}
                min="5"
                step="0.5"
              />
            </label>
          </div>

          <div className="pipeline-section">
            <h3>Pipeline</h3>
            <button onClick={saveTimeline} className="tool-btn">
              💾 Save Config
            </button>
            <button onClick={loadTimeline} className="tool-btn">
              📂 Load Config
            </button>
            <button onClick={validateTimeline} className="tool-btn">
              ✓ Validate
            </button>
          </div>

          {saveMessage && (
            <div className="message">
              {saveMessage}
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="timeline-area">
          <div className="timeline-ruler">
            <div className="ruler-marks" style={{ width: `${duration * pixelsPerSecond}px` }}>
              {Array.from({ length: Math.floor(duration) + 1 }).map((_, i) => (
                <div key={i} className="ruler-mark">
                  <span className="ruler-time">{i}s</span>
                </div>
              ))}
            </div>
          </div>

          <div
            className="tracks-container"
            ref={timelineRef}
            onClick={handleTimelineClick}
          >
            <div
              className="playhead"
              style={{
                left: `${playhead * pixelsPerSecond}px`,
              }}
            />

            {tracks.length === 0 ? (
              <div className="empty-state">
                <p>👈 Add a track to get started</p>
              </div>
            ) : (
              tracks.map((track) => (
                <div
                  key={track.id}
                  className={`track ${track.type} ${!track.visible ? 'hidden' : ''}`}
                >
                  <div className="track-header">
                    <div className="track-meta">
                      <span className="track-icon">
                        {track.type === 'video' ? '🎥' : '🎵'}
                      </span>
                      <span className="track-label">
                        {track.type === 'video' ? 'Video' : 'Audio'} {track.id.slice(-4)}
                      </span>
                    </div>
                    <div className="track-buttons">
                      <button
                        className={`track-btn ${!track.visible ? 'off' : ''}`}
                        onClick={() => toggleTrackVisibility(track.id)}
                        title="Toggle visibility"
                      >
                        {track.visible ? '👁' : '👁‍🗨'}
                      </button>
                      <button
                        className={`track-btn ${track.solo ? 'active' : ''}`}
                        onClick={() =>
                          setTracks(
                            tracks.map((t) =>
                              t.id === track.id ? { ...t, solo: !t.solo } : t
                            )
                          )
                        }
                        title="Solo"
                      >
                        S
                      </button>
                      <button
                        className={`track-btn ${track.locked ? 'active' : ''}`}
                        onClick={() =>
                          setTracks(
                            tracks.map((t) =>
                              t.id === track.id ? { ...t, locked: !t.locked } : t
                            )
                          )
                        }
                        title="Lock track"
                      >
                        🔒
                      </button>
                    </div>
                  </div>

                  <div className="track-content">
                    <div
                      className="track-clips"
                      style={{ width: `${duration * pixelsPerSecond}px` }}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => {
                        e.preventDefault();
                        handleFileImport(track.id, e.dataTransfer.files);
                      }}
                    >
                      {track.clips.length === 0 && (
                        <div className="drop-zone">
                          <label htmlFor={`import-${track.id}`} className="import-label">
                            ⬆ Drop files here or click to import
                          </label>
                          <input
                            id={`import-${track.id}`}
                            type="file"
                            multiple
                            accept={track.type === 'video' ? 'video/*' : 'audio/*'}
                            onChange={(e) => handleFileImport(track.id, e.target.files)}
                            style={{ display: 'none' }}
                          />
                        </div>
                      )}

                      {track.clips.map((clip) => (
                        <TimelineClip
                          key={clip.id}
                          clip={clip}
                          trackId={track.id}
                          pixelsPerSecond={pixelsPerSecond}
                          onPositionChange={(newStart) =>
                            updateClipPosition(track.id, clip.id, newStart)
                          }
                          isSelected={selectedClip?.id === clip.id}
                          onSelect={() => setSelectedClip(clip)}
                          trackType={track.type}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Inspector */}
      {selectedClip && (
        <div className="inspector-panel">
          <h3>📋 Clip Properties</h3>
          <div className="inspector-fields">
            <div className="field">
              <label>Name:</label>
              <span className="value">{selectedClip.name}</span>
            </div>
            <div className="field">
              <label>Start:</label>
              <input
                type="number"
                value={selectedClip.start.toFixed(2)}
                onChange={(e) =>
                  updateClipPosition(
                    tracks.find((t) => t.clips.some((c) => c.id === selectedClip.id))?.id,
                    selectedClip.id,
                    parseFloat(e.target.value)
                  )
                }
                step="0.1"
              />
              <span className="unit">s</span>
            </div>
            <div className="field">
              <label>Duration:</label>
              <span className="value">{selectedClip.duration.toFixed(2)}s</span>
            </div>
            <div className="field">
              <label>Offset:</label>
              <input
                type="number"
                value={selectedClip.offset.toFixed(2)}
                onChange={(e) => {
                  const trackId = tracks.find((t) => t.clips.some((c) => c.id === selectedClip.id))?.id;
                  setTracks(
                    tracks.map((t) =>
                      t.id === trackId
                        ? {
                            ...t,
                            clips: t.clips.map((c) =>
                              c.id === selectedClip.id
                                ? { ...c, offset: parseFloat(e.target.value) }
                                : c
                            ),
                          }
                        : t
                    )
                  );
                }}
                step="0.1"
              />
              <span className="unit">s</span>
            </div>
            <button
              className="delete-btn"
              onClick={() => {
                const trackId = tracks.find((t) => t.clips.some((c) => c.id === selectedClip.id))?.id;
                setTracks(
                  tracks.map((t) =>
                    t.id === trackId
                      ? { ...t, clips: t.clips.filter((c) => c.id !== selectedClip.id) }
                      : t
                  )
                );
                setSelectedClip(null);
              }}
            >
              🗑 Delete Clip
            </button>
          </div>
        </div>
      )}

      {/* Validation Results */}
      {validationResult && (
        <div className="validation-panel">
          <h3>📊 Validation Results</h3>
          <div className="validation-content">
            <p className={`status ${validationResult.valid ? 'valid' : 'invalid'}`}>
              {validationResult.valid ? '✅ VALID' : '❌ INVALID'}
            </p>
            {validationResult.errors && validationResult.errors.length > 0 && (
              <div className="errors">
                <strong>Errors:</strong>
                <ul>
                  {validationResult.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            )}
            {validationResult.warnings && validationResult.warnings.length > 0 && (
              <div className="warnings">
                <strong>Warnings:</strong>
                <ul>
                  {validationResult.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="summary">
              {validationResult.total_clips} clips • 
              {validationResult.video_tracks} video • 
              {validationResult.audio_tracks} audio
            </p>
            <button onClick={() => setValidationResult(null)} className="close-btn">
              ✕ Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Timeline Clip Component
const TimelineClip = ({
  clip,
  trackId,
  pixelsPerSecond,
  onPositionChange,
  isSelected,
  onSelect,
  trackType,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);
  const clipRef = useRef(null);

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragOffset(e.clientX - clipRef.current.getBoundingClientRect().left);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;

    const parentRect = clipRef.current.parentElement.getBoundingClientRect();
    const x = e.clientX - parentRect.left - dragOffset;
    const newStart = x / pixelsPerSecond;

    onPositionChange(newStart);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset, pixelsPerSecond]);

  const width = clip.duration * pixelsPerSecond;
  const left = clip.start * pixelsPerSecond;

  return (
    <div
      ref={clipRef}
      className={`clip ${isSelected ? 'selected' : ''} ${trackType}`}
      style={{
        left: `${left}px`,
        width: `${width}px`,
      }}
      onMouseDown={(e) => {
        handleMouseDown(e);
        onSelect();
      }}
      title={`${clip.name}\n${clip.start.toFixed(2)}s - ${(clip.start + clip.duration).toFixed(2)}s`}
    >
      <div className="clip-header">
        <span className="clip-icon">{trackType === 'video' ? '🎬' : '🎦'}</span>
        <span className="clip-name">{clip.name}</span>
      </div>
      <div className="clip-timeline">
        <span className="clip-time">{clip.start.toFixed(1)}s</span>
      </div>
    </div>
  );
};

// Render App
ReactDOM.render(<TimelineDirector />, document.getElementById('root'));
