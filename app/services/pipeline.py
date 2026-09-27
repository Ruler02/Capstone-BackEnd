"""Orkestrasi Audio/Teks → ASR → preprocessing → NER → geocoding → notif."""

import re
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entitas import EntitasNer
from app.models.laporan import Laporan
from app.services.asr import AsrEngine, build_asr
from app.services.geocoder import Geocoder, build_geocoder
from app.services.ner import NerEngine, build_ner
from app.services.notifier import Notifier, build_notifier


def preprocess_text(text: str) -> str:
    """Hapus marker noise transkripsi tanpa mengubah teks asli yang disimpan."""
    cleaned = re.sub(r"\[[^\]]*\]", " ", text)
    cleaned = re.sub(r">>+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def run_pipeline(
    db: Session,
    laporan_id: str,
    *,
    asr: AsrEngine | None = None,
    ner: NerEngine | None = None,
    geocoder: Geocoder | None = None,
    notifier: Notifier | None = None,
) -> None:
    laporan = db.get(Laporan, laporan_id)
    if laporan is None:
        raise ValueError(f"Laporan tidak ditemukan: {laporan_id}")

    settings = get_settings()
    asr = asr or build_asr(settings)
    ner = ner or build_ner(settings)
    geocoder = geocoder or build_geocoder(settings)
    notifier = notifier or build_notifier(settings)

    try:
        if laporan.sumber_input == "audio":
            if not laporan.audio_path or not Path(laporan.audio_path).exists():
                raise FileNotFoundError("File audio laporan tidak ditemukan")
            laporan.konten_teks = asr.transcribe(laporan.audio_path)

        if not laporan.konten_teks or not laporan.konten_teks.strip():
            raise ValueError("Konten teks laporan kosong")

        normalized = preprocess_text(laporan.konten_teks)
        db.execute(delete(EntitasNer).where(EntitasNer.id_laporan == laporan.id_laporan))
        for extracted in ner.extract(normalized):
            latitude = longitude = None
            if extracted.jenis_entitas == "Location":
                coordinates = geocoder.geocode(extracted.nilai_teks)
                if coordinates:
                    latitude, longitude = coordinates
            db.add(
                EntitasNer(
                    id_laporan=laporan.id_laporan,
                    jenis_entitas=extracted.jenis_entitas,
                    nilai_teks=extracted.nilai_teks,
                    latitude=latitude,
                    longitude=longitude,
                )
            )

        laporan.status_proses = "selesai"
        laporan.status_verifikasi = "menunggu_verifikasi"
        laporan.pesan_gagal = None
        db.commit()

        if laporan.phone_pelapor:
            notifier.send(laporan.phone_pelapor, f"ID laporan kamu: {laporan.id_laporan}")
    except Exception as exc:
        db.rollback()
        laporan = db.get(Laporan, laporan_id)
        if laporan:
            laporan.status_proses = "gagal"
            laporan.pesan_gagal = str(exc)[:1000]
            db.commit()
        raise
