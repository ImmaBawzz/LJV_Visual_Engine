"""
LJV Content Engine — Main AI Generation Pipeline

Integrates artist persona generation, lyric writing, video scripting,
music composition, and platform publishing into a single orchestrator
that mirrors the step-numbered structure of the existing LJV Visual Engine.

Usage (CLI)
-----------
    python -m ai_content.ljv_content_engine \
        --genre pop --background "New York" --theme love --mood happy \
        --style contemporary --bpm 120 \
        --video-path 04_OUTPUT/youtube_16x9/output.mp4 \
        --publish-youtube --publish-spotify

Usage (programmatic)
--------------------
    from ai_content import LJVContentEngine

    engine = LJVContentEngine()
    result = engine.generate_content({
        "genre": "pop",
        "background": "New York",
        "theme": "love",
        "mood": "happy",
        "style": "contemporary",
        "bpm": 120,
    })
    engine.publish_content(
        video_path=Path("04_OUTPUT/youtube_16x9/output.mp4"),
        youtube=True,
        spotify=True,
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
_LOG_FILE = ROOT / "03_WORK" / "logs" / "ai_content.log"
_RESULT_FILE = ROOT / "03_WORK" / "automation" / "ai_content_result.json"


def _log(msg: str) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.info(msg)
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ContentResult:
    """
    Holds all generated artefacts produced by a single engine run.

    Attributes
    ----------
    biography : str
        Generated artist biography text.
    lyrics : str
        Generated song lyrics.
    video_script : str
        Generated music video script.
    midi_path : Path or None
        Path to the generated MIDI file.
    biography_path : Path or None
        Path to the saved biography file.
    lyrics_path : Path or None
        Path to the saved lyrics file.
    script_path : Path or None
        Path to the saved video script file.
    youtube_response : dict
        YouTube API upload response (empty if not published).
    spotify_response : dict
        Spotify API response (empty if not published).
    errors : list of str
        Any non-fatal errors encountered during generation.
    """

    biography: str = ""
    lyrics: str = ""
    video_script: str = ""
    midi_path: Optional[Path] = None
    biography_path: Optional[Path] = None
    lyrics_path: Optional[Path] = None
    script_path: Optional[Path] = None
    youtube_response: Dict = field(default_factory=dict)
    spotify_response: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = asdict(self)
        # Convert Path objects to strings for JSON serialisation
        for key in ("midi_path", "biography_path", "lyrics_path", "script_path"):
            if d[key] is not None:
                d[key] = str(d[key])
        return d


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class LJVContentEngine:
    """
    Orchestrates the full AI content generation and publishing pipeline.

    Steps
    -----
    1. Generate artist biography       (PersonaGenerator / bart-large-cnn)
    2. Generate song lyrics            (LyricsGenerator  / gpt2 by default)
    3. Generate music video script     (VideoScriptGenerator / t5-base)
    4. Generate MIDI composition       (MusicComposer / music21)
    5. Publish to YouTube              (YouTubePublisher — optional)
    6. Publish / manage Spotify        (SpotifyPublisher — optional)

    Parameters
    ----------
    device : int
        Torch device for all inference steps. -1 = CPU; 0 = first GPU.
    lyrics_model : str, optional
        Override the lyrics generation model.
    script_model : str, optional
        Override the video script model.
    biography_model : str, optional
        Override the biography model.
    use_bert_features : bool
        Pass True to also run lyricsgenius/poet-bert feature extraction.
    """

    def __init__(
        self,
        device: int = -1,
        lyrics_model: Optional[str] = None,
        script_model: Optional[str] = None,
        biography_model: Optional[str] = None,
        use_bert_features: bool = False,
    ) -> None:
        # Import sub-modules lazily so the engine can be imported without
        # all ML dependencies being present (useful for dry-run inspection).
        from .persona_generator import PersonaGenerator
        from .lyrics_generator import LyricsGenerator
        from .video_script_generator import VideoScriptGenerator
        from .music_composer import MusicComposer
        from .publisher import Publisher

        self._persona_gen = PersonaGenerator(model_id=biography_model, device=device)
        self._lyrics_gen = LyricsGenerator(
            model_id=lyrics_model,
            device=device,
            use_bert_features=use_bert_features,
        )
        self._script_gen = VideoScriptGenerator(model_id=script_model, device=device)
        self._composer = MusicComposer()
        self._publisher = Publisher()

        self._result: Optional[ContentResult] = None

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    def _step_biography(self, characteristics: Dict, result: ContentResult) -> None:
        _log("[Engine] Step 1: Generating artist biography...")
        try:
            biography = self._persona_gen.generate_biography(characteristics)
            path = self._persona_gen.save_biography(biography)
            result.biography = biography
            result.biography_path = path
            _log(f"[Engine] Biography done ({len(biography)} chars).")
        except Exception as exc:
            msg = f"Biography generation failed: {exc}"
            _log(f"[Engine] WARNING: {msg}")
            result.errors.append(msg)

    def _step_lyrics(self, characteristics: Dict, result: ContentResult) -> None:
        _log("[Engine] Step 2: Generating lyrics...")
        try:
            output = self._lyrics_gen.generate_lyrics(characteristics)
            lyrics = output["lyrics"]
            path = self._lyrics_gen.save_lyrics(lyrics)
            result.lyrics = lyrics
            result.lyrics_path = path
            _log(f"[Engine] Lyrics done ({len(lyrics)} chars).")
        except Exception as exc:
            msg = f"Lyrics generation failed: {exc}"
            _log(f"[Engine] WARNING: {msg}")
            result.errors.append(msg)

    def _step_video_script(self, characteristics: Dict, result: ContentResult) -> None:
        _log("[Engine] Step 3: Generating video script...")
        # Use generated biography as the artist context if available
        artist_ctx = result.biography or characteristics.get("artist", "LJV")
        lyrics_ctx = result.lyrics or characteristics.get("lyrics", "")
        try:
            script = self._script_gen.generate_video_script(
                lyrics=lyrics_ctx,
                artist=artist_ctx,
                genre=characteristics.get("genre", ""),
                mood=characteristics.get("mood", ""),
                visual_theme=characteristics.get("visual_theme", ""),
            )
            path = self._script_gen.save_script(script)
            result.video_script = script
            result.script_path = path
            _log(f"[Engine] Script done ({len(script)} chars).")
        except Exception as exc:
            msg = f"Video script generation failed: {exc}"
            _log(f"[Engine] WARNING: {msg}")
            result.errors.append(msg)

    def _step_music(self, characteristics: Dict, result: ContentResult) -> None:
        _log("[Engine] Step 4: Composing MIDI...")
        try:
            midi_path = self._composer.generate_music_from_config(characteristics)
            result.midi_path = midi_path
            _log(f"[Engine] MIDI done: {midi_path}")
        except Exception as exc:
            msg = f"Music composition failed: {exc}"
            _log(f"[Engine] WARNING: {msg}")
            result.errors.append(msg)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_content(self, characteristics: Dict) -> ContentResult:
        """
        Run all four generation steps and return a ContentResult.

        Parameters
        ----------
        characteristics : dict
            Keys used across steps:
              - ``genre``        : music genre (e.g. "pop")
              - ``background``   : artist origin (e.g. "New York")
              - ``theme``        : lyric theme (e.g. "love")
              - ``mood``         : mood/tone (e.g. "happy")
              - ``style``        : style descriptor (e.g. "contemporary")
              - ``bpm``          : tempo in BPM for MIDI (int, default 120)
              - ``visual_theme`` : video visual concept (optional)
              - ``influences``   : artist influences (optional)
              - ``artist``       : artist name fallback (default "LJV")

        Returns
        -------
        ContentResult
        """
        _log(f"[Engine] Starting content generation. Characteristics: {characteristics}")
        result = ContentResult()

        self._step_biography(characteristics, result)
        self._step_lyrics(characteristics, result)
        self._step_video_script(characteristics, result)
        self._step_music(characteristics, result)

        # Persist result summary
        _RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
        _RESULT_FILE.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _log(f"[Engine] All steps complete. Result saved: {_RESULT_FILE}")
        if result.errors:
            _log(f"[Engine] {len(result.errors)} step(s) had errors: {result.errors}")

        self._result = result
        return result

    def publish_content(
        self,
        video_path: Optional[Path] = None,
        youtube: bool = False,
        spotify: bool = False,
        youtube_title: Optional[str] = None,
        youtube_description: Optional[str] = None,
        youtube_tags: Optional[list] = None,
        youtube_privacy: str = "unlisted",
        spotify_playlist_name: Optional[str] = None,
        spotify_track_name: Optional[str] = None,
        spotify_artist_name: str = "LJV",
    ) -> ContentResult:
        """
        Optionally publish generated content to YouTube and/or Spotify.

        ``generate_content()`` must be called first (or pass an external
        ContentResult via ``result``).  Publishing steps run independently
        — a failure in one does not abort the other.

        Parameters
        ----------
        video_path : Path, optional
            Path to the rendered video file for YouTube upload.
        youtube : bool
            If True, upload to YouTube.
        spotify : bool
            If True, manage Spotify release playlist.
        youtube_title : str, optional
            Defaults to artist biography first sentence if available.
        youtube_description : str, optional
            Defaults to generated lyrics excerpt.
        youtube_tags : list, optional
        youtube_privacy : str
            "public", "unlisted", or "private". Default "unlisted".
        spotify_playlist_name : str, optional
            Defaults to "LJV Release".
        spotify_track_name : str, optional
            Track name to search for on Spotify post-distribution.
        spotify_artist_name : str

        Returns
        -------
        ContentResult
            Updated result with publishing responses.
        """
        result = self._result or ContentResult()

        if youtube:
            if not video_path or not Path(video_path).exists():
                msg = f"YouTube publish skipped: video file not found ({video_path})"
                _log(f"[Engine] WARNING: {msg}")
                result.errors.append(msg)
            else:
                _log("[Engine] Step 5: Publishing to YouTube...")
                title = youtube_title or "LJV — New Release"
                description = youtube_description or result.lyrics[:500]
                try:
                    response = self._publisher.publish_to_youtube(
                        video_path=Path(video_path),
                        title=title,
                        description=description,
                        tags=youtube_tags or [],
                        privacy=youtube_privacy,
                    )
                    result.youtube_response = response
                    _log(f"[Engine] YouTube upload complete: {response.get('id', '?')}")
                except Exception as exc:
                    msg = f"YouTube publish failed: {exc}"
                    _log(f"[Engine] WARNING: {msg}")
                    result.errors.append(msg)

        if spotify:
            _log("[Engine] Step 6: Managing Spotify release...")
            pl_name = spotify_playlist_name or "LJV Release"
            track = spotify_track_name or "Velocity Letters"
            try:
                response = self._publisher.publish_to_spotify(
                    playlist_name=pl_name,
                    track_name=track,
                    artist_name=spotify_artist_name,
                )
                result.spotify_response = response
                if response:
                    _log("[Engine] Spotify playlist updated.")
                else:
                    _log("[Engine] Spotify: track not found (may need distribution first).")
            except Exception as exc:
                msg = f"Spotify publish failed: {exc}"
                _log(f"[Engine] WARNING: {msg}")
                result.errors.append(msg)

        # Re-save result with publishing data
        _RESULT_FILE.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._result = result
        return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="LJV Content Engine — AI generation + publishing pipeline"
    )
    # Generation parameters
    parser.add_argument("--genre", default="pop")
    parser.add_argument("--background", default="New York")
    parser.add_argument("--theme", default="love")
    parser.add_argument("--mood", default="happy")
    parser.add_argument("--style", default="contemporary")
    parser.add_argument("--bpm", type=int, default=120)
    parser.add_argument("--visual-theme", default="")
    parser.add_argument("--influences", default="")
    parser.add_argument("--artist", default="LJV")
    # Model overrides
    parser.add_argument("--lyrics-model", default=None)
    parser.add_argument("--script-model", default=None)
    parser.add_argument("--biography-model", default=None)
    parser.add_argument("--bert-features", action="store_true")
    parser.add_argument("--device", type=int, default=-1)
    # Publishing
    parser.add_argument("--publish-youtube", action="store_true")
    parser.add_argument("--publish-spotify", action="store_true")
    parser.add_argument("--video-path", default=None)
    parser.add_argument("--youtube-title", default=None)
    parser.add_argument("--youtube-description", default=None)
    parser.add_argument("--youtube-privacy", default="unlisted")
    parser.add_argument("--spotify-playlist", default="LJV Release")
    parser.add_argument("--spotify-track", default=None)

    args = parser.parse_args()

    characteristics = {
        "genre": args.genre,
        "background": args.background,
        "theme": args.theme,
        "mood": args.mood,
        "style": args.style,
        "bpm": args.bpm,
        "visual_theme": args.visual_theme,
        "influences": args.influences,
        "artist": args.artist,
    }

    engine = LJVContentEngine(
        device=args.device,
        lyrics_model=args.lyrics_model,
        script_model=args.script_model,
        biography_model=args.biography_model,
        use_bert_features=args.bert_features,
    )

    result = engine.generate_content(characteristics)

    print("\n=== Biography ===")
    print(result.biography or "(not generated)")
    print("\n=== Lyrics ===")
    print(result.lyrics[:400] + "..." if len(result.lyrics) > 400 else result.lyrics or "(not generated)")
    print("\n=== Video Script ===")
    print(result.video_script[:400] + "..." if len(result.video_script) > 400 else result.video_script or "(not generated)")
    print(f"\nMIDI: {result.midi_path or '(not generated)'}")

    if result.errors:
        print(f"\nWarnings ({len(result.errors)}):")
        for err in result.errors:
            print(f"  - {err}")

    if args.publish_youtube or args.publish_spotify:
        engine.publish_content(
            video_path=Path(args.video_path) if args.video_path else None,
            youtube=args.publish_youtube,
            spotify=args.publish_spotify,
            youtube_title=args.youtube_title,
            youtube_description=args.youtube_description,
            youtube_privacy=args.youtube_privacy,
            spotify_playlist_name=args.spotify_playlist,
            spotify_track_name=args.spotify_track or args.theme,
            spotify_artist_name=args.artist,
        )
