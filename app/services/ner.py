"""Kontrak dan implementasi NER dengan empat label proposal."""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings

ALLOWED_ENTITY_TYPES = {"Person", "Date", "Location", "Disaster"}


@dataclass(frozen=True)
class ExtractedEntity:
    jenis_entitas: str
    nilai_teks: str
    char_start: int = 0
    char_end: int = 0


class NerEngine(Protocol):
    def extract(self, text: str) -> list[ExtractedEntity]: ...


class FakeNer:
    def extract(self, text: str) -> list[ExtractedEntity]:
        return [
            ExtractedEntity("Disaster", "banjir"),
            ExtractedEntity("Location", "Surabaya"),
            ExtractedEntity("Date", "lima Januari"),
            ExtractedEntity("Person", "warga"),
        ]


class TransformersNer:
    def __init__(self, model_path: str):
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError("Install transformers untuk NER backend transformers") from exc
        self._pipeline = pipeline("token-classification", model=model_path, aggregation_strategy="simple")

    def extract(self, text: str) -> list[ExtractedEntity]:
        entities = []
        for item in self._pipeline(text):
            label = item["entity_group"].title()
            if label in ALLOWED_ENTITY_TYPES:
                entities.append(
                    ExtractedEntity(
                        jenis_entitas=label,
                        nilai_teks=item["word"].strip(),
                        char_start=item.get("start", 0),
                        char_end=item.get("end", 0),
                    )
                )
        return entities


def build_ner(settings: Settings) -> NerEngine:
    if settings.ner_backend == "fake":
        return FakeNer()
    if settings.ner_backend == "transformers":
        if not settings.ner_model_path:
            raise ValueError("NER_MODEL_PATH wajib diisi untuk backend transformers")
        return TransformersNer(settings.ner_model_path)
    raise ValueError(f"NER backend tidak dikenal: {settings.ner_backend}")
