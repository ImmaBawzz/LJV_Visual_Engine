import React, { useState, useRef, useEffect } from 'react';
import './TimelineDirector.css';

const TimelineDirector = () => {
  const [tracks, setTracks] = useState([]);
  const [playhead, setPlayhead] = useState(0);
  const [duration, setDuration] = useState(120);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedClip, setSelectedClip] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [showMarkers, setShowMarkers] = useState(true);
  const timelineRef = useRef(null);
  const playbackRef = useRef(null);

  // Add new track
  const addTrack = (type) => {
    const newTrack = {
      id: `${type}-${Date.now()}`,
      type, // 'audio' or 'video'
      clips: [],
      visible: true,
      solo: false,
      locked: false,
      volume: 100,
      opacity: 100,
    };
    setTracks([...tracks, newTrack]);
  };

  // Handle file import
  const handleFileImport = (trackId, files) => {
    Array.from(files).forEach((file) => {
      const clip = {
        id: `${trackId}-clip-${Date.now()}`,
        name: file.name,
        start: 0,
        duration: 5, // Default 5 seconds
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

  // Update clip position on timeline
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

  // Handle timeline click for playhead positioning
  const handleTimelineClick = (e) => {
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
          return prev + 0.016; // ~60fps
        });
      }, 16);
    }
    return () => clearInterval(interval);
  }, [isPlaying, duration]);

  const pixelsPerSecond = 50 * zoom;

  return (
    <div className="timeline-director">
      {/* Header Controls */}
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
        {/* Sidebar - Track Controls */}
        <div className="track-controls-sidebar">
          <div className="add-track-section">
            <h3>Tracks</h3>
            <button
              onClick={() => addTrack('video')}
              className="add-track-btn video-btn"
            >
              + Video
            </button>
            <button
              onClick={() => addTrack('audio')}
              className="add-track-btn audio-btn"
            >
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
        </div>

        {/* Main Timeline Area */}
        <div className="timeline-area">
          {/* Timeline Ruler */}
          <div className="timeline-ruler">
            <div className="ruler-marks" style={{ width: `${duration * pixelsPerSecond}px` }}>
              {Array.from({ length: Math.floor(duration) + 1 }).map((_, i) => (
                <div key={i} className="ruler-mark">
                  <span className="ruler-time">{i}s</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tracks Container */}
          <div
            className="tracks-container"
            ref={timelineRef}
            onClick={handleTimelineClick}
          >
            {/* Playhead Line */}
            <div
              className="playhead"
              style={{
                left: `${playhead * pixelsPerSecond}px`,
              }}
            />

            {/* Tracks */}
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
                  {/* Track Header */}
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

                  {/* Track Content */}
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

                      {/* Clips */}
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

      {/* Inspector Panel */}
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
    </div>
  );
};

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

export default TimelineDirector;
