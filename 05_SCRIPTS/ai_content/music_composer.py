"""
Music Composer

Procedurally generates melodies and harmonies using the ``music21``
library and exports them as MIDI files.

Bug fixes vs. original request
-------------------------------
``note.Note`` does NOT accept a bare integer as a pitch argument — it
expects a pitch name string like ``"C4"`` or a ``music21.pitch.Pitch``
object.  The original code passed ``np.random.randint(60, 72)`` directly,
which raised a ``TypeError``.  This module converts MIDI integers to
``Pitch`` objects via ``pitch.Pitch(midi=n)`` before construction.

``stream.Stream.append()`` takes a single element, not a list.  The
original code called ``s.append(melody)`` where ``melody`` was a Python
list, which silently dropped the notes.  This module uses
``stream.Part`` containers and ``stream.Score`` composition instead,
which is the idiomatic music21 pattern.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
_LOG_FILE = ROOT / "03_WORK" / "logs" / "ai_content.log"
_DEFAULT_OUTPUT = ROOT / "03_WORK" / "automation" / "generated_music.mid"


def _log(msg: str) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.info(msg)
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


class MusicComposer:
    """
    Procedural melody + harmony composer built on ``music21``.

    Generates a melody of random pitches within a configurable MIDI range,
    adds a parallel harmony voice transposed by a fixed interval (default:
    one octave up), and writes the result to a MIDI file.

    For richer compositions, this class can be extended with:
    - Key/scale constraint (restrict pitches to a diatonic set)
    - Rhythm patterns aligned to song BPM
    - Chord progressions as a bass voice
    - Integration with amper-music REST API for AI-generated backing tracks

    Parameters
    ----------
    midi_low : int
        Lowest MIDI pitch (inclusive) for melody. Default 60 = C4.
    midi_high : int
        Highest MIDI pitch (exclusive) for melody. Default 84 = C6.
    note_count : int
        Number of melody notes to generate. Default 16.
    harmony_semitones : int
        Semitone offset for harmony voice. Default 12 (one octave up).

    Example
    -------
    >>> composer = MusicComposer()
    >>> path = composer.generate_music(genre="pop", style="contemporary", mood="happy")
    >>> print(path)
    """

    def __init__(
        self,
        midi_low: int = 60,
        midi_high: int = 84,
        note_count: int = 16,
        harmony_semitones: int = 12,
        seed: Optional[int] = None,
    ) -> None:
        self.midi_low = midi_low
        self.midi_high = midi_high
        self.note_count = note_count
        self.harmony_semitones = harmony_semitones
        self.seed = seed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _midi_to_pitch_name(self, midi_val: int) -> str:
        """Convert a MIDI integer to a music21 pitch name string (e.g. 'C4')."""
        try:
            from music21 import pitch as m21pitch
        except ImportError as exc:
            raise ImportError(
                "music21 is required for MusicComposer. "
                "Install it with: pip install music21"
            ) from exc
        return m21pitch.Pitch(midi=int(midi_val)).nameWithOctave

    def _build_melody(self, rng) -> List:
        """Return a list of music21 ``note.Note`` objects forming a melody."""
        from music21 import note as m21note, duration

        melody: List[m21note.Note] = []
        for _ in range(self.note_count):
            midi_val = int(rng.integers(self.midi_low, self.midi_high))
            pitch_name = self._midi_to_pitch_name(midi_val)
            n = m21note.Note(pitch_name)
            # Random quarter-length between 0.5 and 2.0 beats
            n.duration = duration.Duration(quarterLength=float(rng.uniform(0.5, 2.0)))
            melody.append(n)
        return melody

    def _build_harmony(self, melody: List) -> List:
        """Return a harmony voice transposed from the melody."""
        from music21 import note as m21note, duration, interval

        harmony: List[m21note.Note] = []
        offset = interval.Interval(self.harmony_semitones)
        for src in melody:
            transposed_pitch = src.pitch.transpose(offset)
            n = m21note.Note(transposed_pitch.nameWithOctave)
            n.duration = duration.Duration(quarterLength=src.duration.quarterLength)
            harmony.append(n)
        return harmony

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_music(
        self,
        genre: str = "pop",
        style: str = "contemporary",
        mood: str = "happy",
        output_path: Optional[Path] = None,
        bpm: int = 120,
    ) -> Path:
        """
        Generate a two-voice (melody + harmony) MIDI composition.

        Parameters
        ----------
        genre : str
            Music genre label (informational; used in log and filename).
        style : str
            Style descriptor (informational).
        mood : str
            Mood descriptor (informational).
        output_path : Path, optional
            Destination MIDI path. Defaults to 03_WORK/automation/generated_music.mid.
        bpm : int
            Tempo in beats-per-minute embedded in the MIDI file.

        Returns
        -------
        Path
            Absolute path to the written MIDI file.
        """
        try:
            import numpy as np
            from music21 import stream as m21stream, tempo as m21tempo
        except ImportError as exc:
            raise ImportError(
                "music21 and numpy are required for MusicComposer. "
                "Install them with: pip install music21 numpy"
            ) from exc

        rng = np.random.default_rng(self.seed)

        melody = self._build_melody(rng)
        harmony = self._build_harmony(melody)

        # Build score: melody in part 1, harmony in part 2
        score = m21stream.Score()

        melody_part = m21stream.Part(id="Melody")
        melody_part.insert(0, m21tempo.MetronomeMark(number=bpm))
        for n in melody:
            melody_part.append(n)

        harmony_part = m21stream.Part(id="Harmony")
        for n in harmony:
            harmony_part.append(n)

        score.append(melody_part)
        score.append(harmony_part)

        if output_path is None:
            output_path = _DEFAULT_OUTPUT
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        score.write("midi", fp=str(output_path))
        _log(
            f"[MusicComposer] MIDI written: {output_path} "
            f"(genre={genre}, style={style}, mood={mood}, bpm={bpm}, "
            f"notes={self.note_count})"
        )
        return output_path

    def generate_music_from_config(self, config: Dict) -> Path:
        """
        Convenience wrapper accepting a characteristics dict from the pipeline.

        Reads keys: ``genre``, ``style``, ``mood``, ``bpm`` (optional).
        """
        return self.generate_music(
            genre=config.get("genre", "pop"),
            style=config.get("style", "contemporary"),
            mood=config.get("mood", "happy"),
            bpm=config.get("bpm", 120),
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a MIDI composition.")
    parser.add_argument("--genre", default="pop")
    parser.add_argument("--style", default="contemporary")
    parser.add_argument("--mood", default="happy")
    parser.add_argument("--bpm", type=int, default=120)
    parser.add_argument("--notes", type=int, default=16)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", default=None, help="Output MIDI path")
    args = parser.parse_args()

    out = Path(args.output) if args.output else None
    composer = MusicComposer(note_count=args.notes, seed=args.seed)
    midi_path = composer.generate_music(
        genre=args.genre,
        style=args.style,
        mood=args.mood,
        output_path=out,
        bpm=args.bpm,
    )
    print(f"MIDI saved to: {midi_path}")
