"""
Music Video Script Generator

Generates a scene-by-scene music video shooting script from lyrics and
artist context using Google's t5-base seq2seq model.

t5-base is a solid general-purpose seq2seq model for instruction-following
tasks with prompts formatted as ``"<task>: <input>"``.
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
_LOG_FILE = ROOT / "03_WORK" / "logs" / "ai_content.log"


def _log(msg: str) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.info(msg)
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


class VideoScriptGenerator:
    """
    Generates a music video shooting script using ``t5-base``.

    The prompt framing ("summarize:", "translate:", etc.) used by T5 models
    is not required for generative tasks — instead we frame the input as a
    natural task description which t5-base handles well via its span-corruption
    denoising pre-training.

    For higher-quality scripts, swap in ``google/flan-t5-large`` or
    ``google/flan-t5-xl`` which are instruction-tuned variants of T5.

    Example
    -------
    >>> gen = VideoScriptGenerator()
    >>> script = gen.generate_video_script(lyrics="...", artist="LJV")
    >>> print(script)
    """

    MODEL_ID = "t5-base"

    def __init__(self, model_id: Optional[str] = None, device: int = -1) -> None:
        """
        Parameters
        ----------
        model_id : str, optional
            HuggingFace model ID. ``google/flan-t5-large`` is a strong upgrade.
        device : int
            -1 = CPU; 0 = first CUDA GPU.
        """
        self.model_id = model_id or self.MODEL_ID
        self.device = device
        self._tokenizer = None
        self._model = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from transformers import T5Tokenizer, T5ForConditionalGeneration
        except ImportError as exc:
            raise ImportError(
                "transformers is required for VideoScriptGenerator. "
                "Install it with: pip install transformers torch"
            ) from exc

        _log(f"[VideoScriptGenerator] Loading model: {self.model_id}")
        self._tokenizer = T5Tokenizer.from_pretrained(self.model_id)
        self._model = T5ForConditionalGeneration.from_pretrained(self.model_id)
        if self.device >= 0:
            self._model = self._model.to(f"cuda:{self.device}")
        _log("[VideoScriptGenerator] Model ready.")

    def _build_prompt(
        self,
        lyrics: str,
        artist: str,
        genre: str = "",
        mood: str = "",
        visual_theme: str = "",
    ) -> str:
        # T5 input size limit: 512 tokens. Truncate lyrics to a safe character length.
        lyrics_snippet = textwrap.shorten(lyrics, width=800, placeholder=" [...]")
        parts = [
            "Write a professional music video script with scene descriptions, "
            "camera angles, and visual transitions."
        ]
        parts.append(f"Artist: {artist}.")
        if genre:
            parts.append(f"Genre: {genre}.")
        if mood:
            parts.append(f"Mood: {mood}.")
        if visual_theme:
            parts.append(f"Visual theme: {visual_theme}.")
        parts.append(f"Lyrics: {lyrics_snippet}")
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_video_script(
        self,
        lyrics: str,
        artist: str,
        genre: str = "",
        mood: str = "",
        visual_theme: str = "",
        max_length: int = 512,
        num_beams: int = 4,
    ) -> str:
        """
        Generate a scene-by-scene music video script.

        Parameters
        ----------
        lyrics : str
            Full or excerpt of song lyrics.
        artist : str
            Artist name or biography excerpt.
        genre : str, optional
            Music genre (e.g. "pop", "rock").
        mood : str, optional
            Emotional tone (e.g. "euphoric", "melancholic").
        visual_theme : str, optional
            High-level visual concept (e.g. "neon cityscape at night").
        max_length : int
            Maximum output token length.
        num_beams : int
            Beam search width.

        Returns
        -------
        str
            Generated video script text.
        """
        self._load_model()
        prompt = self._build_prompt(lyrics, artist, genre, mood, visual_theme)
        _log(f"[VideoScriptGenerator] Prompt length: {len(prompt)} chars")

        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True,
        )
        if self.device >= 0:
            inputs = {k: v.to(f"cuda:{self.device}") for k, v in inputs.items()}

        output_ids = self._model.generate(
            **inputs,
            max_length=max_length,
            num_beams=num_beams,
            early_stopping=True,
            no_repeat_ngram_size=3,
        )
        script = self._tokenizer.decode(output_ids[0], skip_special_tokens=True)
        _log(f"[VideoScriptGenerator] Script generated ({len(script)} chars).")
        return script

    def save_script(self, script: str, output_path: Optional[Path] = None) -> Path:
        """Save script to disk; defaults to 03_WORK/automation/video_script.txt."""
        if output_path is None:
            output_path = ROOT / "03_WORK" / "automation" / "video_script.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(script, encoding="utf-8")
        _log(f"[VideoScriptGenerator] Saved to {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a music video script.")
    parser.add_argument("--lyrics", required=True, help="Path to lyrics .txt file or inline text")
    parser.add_argument("--artist", default="LJV")
    parser.add_argument("--genre", default="")
    parser.add_argument("--mood", default="")
    parser.add_argument("--visual-theme", default="")
    parser.add_argument("--model", default=VideoScriptGenerator.MODEL_ID)
    args = parser.parse_args()

    # Accept a file path or raw text for --lyrics
    lyrics_path = Path(args.lyrics)
    lyrics_text = lyrics_path.read_text(encoding="utf-8") if lyrics_path.exists() else args.lyrics

    gen = VideoScriptGenerator(model_id=args.model)
    script = gen.generate_video_script(
        lyrics=lyrics_text,
        artist=args.artist,
        genre=args.genre,
        mood=args.mood,
        visual_theme=args.visual_theme,
    )
    path = gen.save_script(script)
    print(script)
    print(f"\nSaved to: {path}")
