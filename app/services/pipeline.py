"""Orkestrasi Audio/Teks → ASR → preprocessing → NER → geocoding → notif."""

import os
import re
import tempfile
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
from app.services.storage import build_storage


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
            if not laporan.audio_path:
                raise FileNotFoundError("File audio laporan tidak ditemukan")
            audio_path = Path(laporan.audio_path)
            temporary_path: Path | None = None
            if not audio_path.exists():
                storage = build_storage(settings)
                # Bucket persisten menyimpan path `r2://`/`supabase://`; unduh
                # dulu ke file sementara sebelum ASR membacanya.
                if not hasattr(storage, "download"):
                    raise FileNotFoundError("File audio laporan tidak ditemukan")
                handle, temp_name = tempfile.mkstemp(suffix=audio_path.suffix)
                os.close(handle)
                temporary_path = Path(temp_name)
                audio_path = storage.download(laporan.audio_path, temporary_path)
            try:
                laporan.konten_teks = asr.transcribe(str(audio_path))
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

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
