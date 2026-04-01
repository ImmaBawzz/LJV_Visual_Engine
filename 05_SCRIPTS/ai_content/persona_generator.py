"""
Artist Persona Generator

Generates artist biographies and persona descriptions using
facebook/bart-large-cnn (seq2seq summarization/generation model).

Note: bart-large-cnn is fine-tuned for summarization but works well
for conditional text generation when given a descriptive prompt prefix.
For pure creative generation, consider facebook/bart-large or a GPT-2
family model as an alternative.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
_LOG_FILE = ROOT / "03_WORK" / "logs" / "ai_content.log"


def _log(msg: str) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.info(msg)
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


class PersonaGenerator:
    """
    Generates artist biography text from genre/background characteristics.

    Uses facebook/bart-large-cnn for conditional text generation.
    Model is loaded lazily on first call to avoid import-time overhead.

    Example
    -------
    >>> gen = PersonaGenerator()
    >>> bio = gen.generate_biography({"genre": "pop", "background": "New York"})
    >>> print(bio)
    """

    MODEL_ID = "facebook/bart-large-cnn"

    def __init__(self, model_id: Optional[str] = None, device: int = -1) -> None:
        """
        Parameters
        ----------
        model_id : str, optional
            HuggingFace model identifier. Defaults to facebook/bart-large-cnn.
        device : int
            Torch device index. -1 = CPU; 0 = first CUDA GPU.
        """
        self.model_id = model_id or self.MODEL_ID
        self.device = device
        self._tokenizer = None
        self._model = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Lazy-load tokenizer and model on first inference call."""
        if self._model is not None:
            return
        try:
            from transformers import BartTokenizer, BartForConditionalGeneration
        except ImportError as exc:
            raise ImportError(
                "transformers is required for PersonaGenerator. "
                "Install it with: pip install transformers torch"
            ) from exc

        _log(f"[PersonaGenerator] Loading model: {self.model_id}")
        self._tokenizer = BartTokenizer.from_pretrained(self.model_id)
        self._model = BartForConditionalGeneration.from_pretrained(self.model_id)
        if self.device >= 0:
            self._model = self._model.to(f"cuda:{self.device}")
        _log("[PersonaGenerator] Model ready.")

    def _build_prompt(self, characteristics: Dict[str, Any]) -> str:
        genre = characteristics.get("genre", "music")
        background = characteristics.get("background", "an unknown city")
        style = characteristics.get("style", "")
        influences = characteristics.get("influences", "")
        mood = characteristics.get("mood", "")

        parts = [f"Artist biography: {genre} musician from {background}."]
        if style:
            parts.append(f"Musical style: {style}.")
        if influences:
            parts.append(f"Influences: {influences}.")
        if mood:
            parts.append(f"Mood and themes: {mood}.")
        parts.append(
            "Write a compelling two-paragraph artist biography in third-person prose."
        )
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_biography(
        self,
        characteristics: Dict[str, Any],
        max_length: int = 256,
        min_length: int = 80,
        num_beams: int = 4,
    ) -> str:
        """
        Generate an artist biography from a characteristics dictionary.

        Parameters
        ----------
        characteristics : dict
            Keys: genre, background, style (opt.), influences (opt.), mood (opt.)
        max_length : int
            Maximum token length for the generated text.
        min_length : int
            Minimum token length for the generated text.
        num_beams : int
            Beam search width. Higher = better quality, slower.

        Returns
        -------
        str
            Generated biography text.
        """
        self._load_model()
        prompt = self._build_prompt(characteristics)
        _log(f"[PersonaGenerator] Prompt: {prompt[:120]}...")

        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
        )
        if self.device >= 0:
            inputs = {k: v.to(f"cuda:{self.device}") for k, v in inputs.items()}

        output_ids = self._model.generate(
            **inputs,
            max_length=max_length,
            min_length=min_length,
            num_beams=num_beams,
            early_stopping=True,
            no_repeat_ngram_size=3,
        )
        biography = self._tokenizer.decode(output_ids[0], skip_special_tokens=True)
        _log(f"[PersonaGenerator] Biography generated ({len(biography)} chars).")
        return biography

    def save_biography(self, biography: str, output_path: Optional[Path] = None) -> Path:
        """
        Persist biography to disk and return the written path.

        Defaults to 02_INPUT/branding/artist_biography.txt relative to ROOT.
        """
        if output_path is None:
            output_path = ROOT / "02_INPUT" / "branding" / "artist_biography.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(biography, encoding="utf-8")
        _log(f"[PersonaGenerator] Saved to {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate an artist biography.")
    parser.add_argument("--genre", default="pop")
    parser.add_argument("--background", default="New York")
    parser.add_argument("--style", default="")
    parser.add_argument("--influences", default="")
    parser.add_argument("--mood", default="")
    args = parser.parse_args()

    characteristics = {
        "genre": args.genre,
        "background": args.background,
        "style": args.style,
        "influences": args.influences,
        "mood": args.mood,
    }

    gen = PersonaGenerator()
    bio = gen.generate_biography(characteristics)
    path = gen.save_biography(bio)
    print(bio)
    print(f"\nSaved to: {path}")
