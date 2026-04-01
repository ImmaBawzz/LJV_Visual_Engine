"""
Lyrics Generator

Generates song lyrics using a text-generation pipeline.

Model selection note
--------------------
The original request referenced ``lyricsgenius/poet-bert``, which is a BERT
encoder model fine-tuned for *classification* tasks, not text generation.
BERT's architecture (encoder-only, masked LM) does not support autoregressive
token generation, and its ``last_hidden_state`` produces contextual embeddings,
not readable text.

This module defaults to ``gpt2`` (a proper causal LM) and exposes a
``model_id`` parameter so you can substitute any HuggingFace text-generation
model — e.g. ``"mistralai/Mistral-7B-Instruct-v0.1"`` or a LoRA-tuned lyrics
checkpoint — without changing call sites.

If you specifically need ``lyricsgenius/poet-bert`` features (e.g. lyric style
classification, rhyme scoring), set ``use_bert_features=True`` and a separate
BERT feature extractor will run alongside the generator.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
_LOG_FILE = ROOT / "03_WORK" / "logs" / "ai_content.log"


def _log(msg: str) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.info(msg)
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


class LyricsGenerator:
    """
    Generates song lyrics via a HuggingFace ``text-generation`` pipeline.

    Parameters
    ----------
    model_id : str
        Any causal-LM model from HuggingFace Hub.
        Default: ``"gpt2"`` (small, fast, always available).
        Recommended upgrade: ``"mistralai/Mistral-7B-Instruct-v0.1"`` or a
        dedicated lyrics model such as ``"Xenova/gpt2-lyrics"``.
    device : int
        Torch device index. -1 = CPU; 0 = first CUDA GPU.
    use_bert_features : bool
        When True, also loads ``lyricsgenius/poet-bert`` to compute lyric-style
        feature vectors (returned alongside the lyrics text).

    Example
    -------
    >>> gen = LyricsGenerator()
    >>> result = gen.generate_lyrics({"genre": "rock", "theme": "love"})
    >>> print(result["lyrics"])
    """

    DEFAULT_MODEL = "gpt2"
    BERT_MODEL = "lyricsgenius/poet-bert"

    def __init__(
        self,
        model_id: Optional[str] = None,
        device: int = -1,
        use_bert_features: bool = False,
    ) -> None:
        self.model_id = model_id or self.DEFAULT_MODEL
        self.device = device
        self.use_bert_features = use_bert_features
        self._pipeline = None
        self._bert_tokenizer = None
        self._bert_model = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise ImportError(
                "transformers is required for LyricsGenerator. "
                "Install it with: pip install transformers torch"
            ) from exc

        _log(f"[LyricsGenerator] Loading generator: {self.model_id}")
        self._pipeline = pipeline(
            "text-generation",
            model=self.model_id,
            device=self.device,
        )
        _log("[LyricsGenerator] Generator ready.")

        if self.use_bert_features:
            self._load_bert()

    def _load_bert(self) -> None:
        """Load poet-bert encoder for lyric feature extraction."""
        from transformers import BertTokenizer, BertModel

        _log(f"[LyricsGenerator] Loading BERT features: {self.BERT_MODEL}")
        self._bert_tokenizer = BertTokenizer.from_pretrained(self.BERT_MODEL)
        self._bert_model = BertModel.from_pretrained(self.BERT_MODEL)
        if self.device >= 0:
            self._bert_model = self._bert_model.to(f"cuda:{self.device}")
        _log("[LyricsGenerator] BERT feature model ready.")

    def _build_prompt(self, theme: Dict[str, Any]) -> str:
        genre = theme.get("genre", "pop")
        topic = theme.get("theme", "life")
        mood = theme.get("mood", "")
        style = theme.get("style", "")

        lines = [f"[{genre.upper()} SONG LYRICS]"]
        if mood:
            lines.append(f"[Mood: {mood}]")
        if style:
            lines.append(f"[Style: {style}]")
        lines.append(f"[Theme: {topic}]")
        lines.append("")
        lines.append("[Verse 1]")
        return "\n".join(lines)

    def _extract_bert_features(self, text: str) -> List[float]:
        """Return CLS-token embedding from poet-bert as a float list."""
        import torch

        tokens = self._bert_tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
        )
        if self.device >= 0:
            tokens = {k: v.to(f"cuda:{self.device}") for k, v in tokens.items()}
        with torch.no_grad():
            outputs = self._bert_model(**tokens)
        cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze()
        return cls_embedding.cpu().tolist()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_lyrics(
        self,
        theme: Dict[str, Any],
        max_new_tokens: int = 300,
        temperature: float = 0.9,
        top_p: float = 0.95,
        repetition_penalty: float = 1.2,
    ) -> Dict:
        """
        Generate song lyrics.

        Parameters
        ----------
        theme : dict
            Keys: ``genre``, ``theme``, ``mood`` (opt.), ``style`` (opt.)
        max_new_tokens : int
            Maximum new tokens to generate beyond the prompt.
        temperature : float
            Sampling temperature. Higher = more creative.
        top_p : float
            Nucleus sampling probability.
        repetition_penalty : float
            Penalises repeated n-grams (> 1.0 reduces loops).

        Returns
        -------
        dict
            ``{"lyrics": str, "prompt": str, "bert_features": list | None}``
        """
        self._load_pipeline()
        prompt = self._build_prompt(theme)
        _log(f"[LyricsGenerator] Generating lyrics for genre={theme.get('genre')}, "
             f"theme={theme.get('theme')}")

        outputs = self._pipeline(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            do_sample=True,
            pad_token_id=self._pipeline.tokenizer.eos_token_id,
        )
        full_text: str = outputs[0]["generated_text"]
        # Strip the prompt prefix so callers receive only the lyrics body
        lyrics = full_text[len(prompt):].strip()
        _log(f"[LyricsGenerator] Lyrics generated ({len(lyrics)} chars).")

        bert_features = None
        if self.use_bert_features and self._bert_model is not None:
            bert_features = self._extract_bert_features(lyrics)

        return {
            "lyrics": lyrics,
            "prompt": prompt,
            "bert_features": bert_features,
        }

    def save_lyrics(self, lyrics: str, output_path: Optional[Path] = None) -> Path:
        """Save raw lyrics text; defaults to 02_INPUT/lyrics/lyrics_raw.txt."""
        if output_path is None:
            output_path = ROOT / "02_INPUT" / "lyrics" / "lyrics_raw.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(lyrics, encoding="utf-8")
        _log(f"[LyricsGenerator] Saved to {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate song lyrics.")
    parser.add_argument("--genre", default="rock")
    parser.add_argument("--theme", default="love")
    parser.add_argument("--mood", default="")
    parser.add_argument("--model", default=LyricsGenerator.DEFAULT_MODEL)
    parser.add_argument(
        "--bert-features",
        action="store_true",
        help="Also extract lyricsgenius/poet-bert style features",
    )
    args = parser.parse_args()

    theme = {"genre": args.genre, "theme": args.theme, "mood": args.mood}
    gen = LyricsGenerator(model_id=args.model, use_bert_features=args.bert_features)
    result = gen.generate_lyrics(theme)
    path = gen.save_lyrics(result["lyrics"])
    print(result["lyrics"])
    print(f"\nSaved to: {path}")
