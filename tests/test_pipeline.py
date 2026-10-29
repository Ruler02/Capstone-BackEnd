"""Uji pipeline end-to-end dengan fake backend (tanpa model ML)."""

from app.models.entitas import EntitasNer
from app.models.laporan import Laporan
from app.services.asr import FakeAsr
from app.services.geocoder import FakeGeocoder
from app.services.id import generate_report_id
from app.services.ner import FakeNer
from app.services.pipeline import run_pipeline


class RecordingNotifier:
    def __init__(self):
        self.messages: list[tuple[str, str]] = []

    def send(self, phone: str, message: str) -> None:
        self.messages.append((phone, message))


def _make_laporan(db, laporan_id: str, sumber: str) -> Laporan:
    laporan = Laporan(
        id_laporan=laporan_id,
        sumber_input=sumber,
        konten_teks="Banjir besar di Surabaya tanggal lima Januari, warga mengungsi."
        if sumber == "teks"
        else None,
        phone_pelapor="081234567890",
    )
    db.add(laporan)
    db.commit()
    return laporan


def test_generate_report_id_format():
    report_id = generate_report_id()
    assert report_id.startswith("LPR-")
    assert len(report_id) == 12


def test_text_pipeline_creates_four_entities(db_session):
    _make_laporan(db_session, "LPR-TEST001", "teks")
    notifier = RecordingNotifier()

    run_pipeline(
        db_session,
        "LPR-TEST001",
        notifier=notifier,
        asr=FakeAsr(),
        ner=FakeNer(),
        geocoder=FakeGeocoder(),
    )

    entities = (
        db_session.query(EntitasNer).filter_by(id_laporan="LPR-TEST001").all()
    )
    assert {e.jenis_entitas for e in entities} == {"Person", "Date", "Location", "Disaster"}
    location = next(e for e in entities if e.jenis_entitas == "Location")
    assert location.latitude is not None and location.longitude is not None

    laporan = db_session.get(Laporan, "LPR-TEST001")
    assert laporan.status_proses == "selesai"
    assert laporan.status_verifikasi == "menunggu_verifikasi"
    assert notifier.messages[0][1].endswith("LPR-TEST001")


def test_audio_pipeline_fills_transcription(db_session, tmp_path):
    audio = tmp_path / "suara.webm"
    audio.write_bytes(b"\x00")
    laporan = Laporan(
        id_laporan="LPR-TEST002",
        sumber_input="audio",
        audio_path=str(audio),
        phone_pelapor=None,
    )
    db_session.add(laporan)
    db_session.commit()

    run_pipeline(
        db_session,
        "LPR-TEST002",
        notifier=RecordingNotifier(),
        asr=FakeAsr(),
        ner=FakeNer(),
        geocoder=FakeGeocoder(),
    )

    refreshed = db_session.get(Laporan, "LPR-TEST002")
    assert refreshed.konten_teks and "banjir" in refreshed.konten_teks
    assert refreshed.status_proses == "selesai"
    assert (
        db_session.query(EntitasNer).filter_by(id_laporan="LPR-TEST002").count() == 4
    )


def test_pipeline_marks_failure_when_audio_missing(db_session):
    laporan = Laporan(
        id_laporan="LPR-TEST003",
        sumber_input="audio",
        audio_path="/path/tidak/ada.webm",
    )
    db_session.add(laporan)
    db_session.commit()

    try:
        run_pipeline(
            db_session,
            "LPR-TEST003",
            notifier=RecordingNotifier(),
            asr=FakeAsr(),
            ner=FakeNer(),
            geocoder=FakeGeocoder(),
        )
    except FileNotFoundError:
        pass

    refreshed = db_session.get(Laporan, "LPR-TEST003")
    assert refreshed.status_proses == "gagal"
    assert refreshed.pesan_gagal
