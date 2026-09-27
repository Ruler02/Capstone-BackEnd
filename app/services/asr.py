"""Kontrak dan implementasi ASR.

Backend default `fake` dipakai pada development/CI agar tim frontend bisa
mengembangkan website tanpa download model besar. Backend `whisper` diaktifkan
ketika model fine-tuned Bahasa Indonesia sudah siap.
"""

from pathlib import Path
from typing import Protocol

from app.core.config import Settings


class AsrEngine(Protocol):
    def transcribe(self, audio_path: str) -> str: ...


class FakeAsr:
    def transcribe(self, audio_path: str) -> str:
        return "Laporan bencana banjir di Surabaya pada tanggal lima Januari."


class WhisperAsr:
    def __init__(self, model_name: str = "small"):
        try:
            import whisper
        except ImportError as exc:
            raise RuntimeError("Install openai-whisper untuk ASR backend whisper") from exc
        self._model = whisper.load_model(model_name)

    def transcribe(self, audio_path: str) -> str:
        result = self._model.transcribe(str(Path(audio_path)), language="id")
        return result["text"].strip()


def build_asr(settings: Settings) -> AsrEngine:
    if settings.asr_backend == "fake":
        return FakeAsr()
    if settings.asr_backend == "whisper":
        return WhisperAsr(settings.ner_model_path or "small")
    raise ValueError(f"ASR backend tidak dikenal: {settings.asr_backend}")
