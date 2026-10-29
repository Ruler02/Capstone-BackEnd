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
    """NER dengan checkpoint BERT-CRF milik tim.

    Arsitektur model (BERT -> BiLSTM -> Linear -> CRF) bukan
    `BertForTokenClassification` standar, jadi `pipeline()` bawaan tidak bisa
    memakainya. Implementasi lengkapnya ada di `ner_bert_crf.py`.
    """

    def __init__(self, model_path: str):
        try:
            from app.services.ner_bert_crf import BertCrfNer
        except ImportError as exc:
            raise RuntimeError(
                "Install torch dan transformers untuk NER backend transformers"
            ) from exc
        self._engine = BertCrfNer(model_path)

    def extract(self, text: str) -> list[ExtractedEntity]:
        return self._engine.extract(text)


# Cache engine per path model. Memuat checkpoint BERT-CRF (±500 MB) butuh
# beberapa detik, jadi model harus dibuat satu kali per proses, bukan satu
# kali per laporan. LRU dengan satu slot sudah cukup karena aplikasi memakai
# satu model NER.
_ENGINE_CACHE: dict[str, TransformersNer] = {}


def build_ner(settings: Settings) -> NerEngine:
    if settings.ner_backend == "fake":
        return FakeNer()
    if settings.ner_backend == "transformers":
        if not settings.ner_model_path:
            raise ValueError("NER_MODEL_PATH wajib diisi untuk backend transformers")
        cached = _ENGINE_CACHE.get(settings.ner_model_path)
        if cached is None:
            cached = TransformersNer(settings.ner_model_path)
            _ENGINE_CACHE[settings.ner_model_path] = cached
        return cached
    raise ValueError(f"NER backend tidak dikenal: {settings.ner_backend}")
