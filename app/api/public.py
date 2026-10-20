"""Endpoint publik tanpa login: lapor cepat, cek status, peta kejadian."""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import SessionLocal, get_db
from app.core.config import get_settings
from app.models.entitas import EntitasNer
from app.models.laporan import Laporan
from app.schemas.laporan import MapPoint, ReportAccepted, ReportDetail, ReportStatus
from app.services.id import generate_report_id
from app.services.pipeline import run_pipeline
from app.services.storage import build_storage

router = APIRouter(prefix="/api/v1/public", tags=["public"])

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".mp4"}
MAX_AUDIO_BYTES = 25 * 1024 * 1024


def _process_in_background(laporan_id: str) -> None:
    db = SessionLocal()
    try:
        run_pipeline(db, laporan_id)
    except Exception:
        pass
    finally:
        db.close()


@router.post("/reports", response_model=ReportAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    background_tasks: BackgroundTasks,
    konten_teks: str | None = Form(default=None),
    phone_pelapor: str | None = Form(default=None),
    audio_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> ReportAccepted:
    if not konten_teks and audio_file is None:
        raise HTTPException(400, detail="Laporan harus berupa teks atau audio")
    if audio_file is not None:
        filename = (audio_file.filename or "").lower()
        if not any(filename.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS):
            raise HTTPException(400, detail="Format audio tidak didukung")

    storage = build_storage(get_settings())
    audio_path = None
    sumber = "teks"
    if audio_file is not None:
        data = await audio_file.read()
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(413, detail="Ukuran audio maksimal 25MB")
        audio_path = storage.save(data, audio_file.filename or "audio", "audio")
        sumber = "audio"

    laporan = Laporan(
        id_laporan=generate_report_id(),
        sumber_input=sumber,
        audio_path=audio_path,
        konten_teks=konten_teks,
        phone_pelapor=phone_pelapor,
        status_proses="diproses",
        status_verifikasi="menunggu_verifikasi",
    )
    db.add(laporan)
    db.commit()

    background_tasks.add_task(_process_in_background, laporan.id_laporan)
    return ReportAccepted(
        id_laporan=laporan.id_laporan,
        status="diproses",
        detail="Simpan ID laporan ini untuk mengecek status.",
    )


@router.get("/reports/{id_laporan}/status", response_model=ReportStatus)
def report_status(id_laporan: str, db: Session = Depends(get_db)) -> ReportStatus:
    laporan = db.get(Laporan, id_laporan)
    if laporan is None:
        raise HTTPException(404, detail="ID laporan tidak ditemukan")
    return ReportStatus(
        id_laporan=laporan.id_laporan,
        status_verifikasi=laporan.status_verifikasi,
        status_proses=laporan.status_proses,
        pesan_gagal=laporan.pesan_gagal,
    )


@router.get("/reports/{id_laporan}", response_model=ReportDetail)
def report_detail(id_laporan: str, db: Session = Depends(get_db)) -> ReportDetail:
    laporan = db.get(Laporan, id_laporan)
    if laporan is None:
        raise HTTPException(404, detail="ID laporan tidak ditemukan")
    entities = (
        db.scalars(
            select(EntitasNer).where(EntitasNer.id_laporan == laporan.id_laporan)
        ).all()
    )
    return ReportDetail(
        id_laporan=laporan.id_laporan,
        sumber_input=laporan.sumber_input,
        konten_teks=laporan.konten_teks,
        status_verifikasi=laporan.status_verifikasi,
        status_proses=laporan.status_proses,
        tanggal_lapor=laporan.tanggal_lapor,
        entitas=[
            {
                "id_entitas": e.id_entitas,
                "jenis_entitas": e.jenis_entitas,
                "nilai_teks": e.nilai_teks,
                "latitude": e.latitude,
                "longitude": e.longitude,
            }
            for e in entities
        ],
    )


@router.get("/map/incidents", response_model=list[MapPoint])
def map_incidents(db: Session = Depends(get_db)) -> list[MapPoint]:
    rows = db.execute(
        select(EntitasNer, Laporan)
        .options(selectinload(Laporan.entitas), selectinload(Laporan.kasus))
        .join(Laporan, EntitasNer.id_laporan == Laporan.id_laporan)
        .where(
            EntitasNer.jenis_entitas == "Location",
            EntitasNer.latitude.is_not(None),
            Laporan.status_verifikasi == "terverifikasi",
        )
    ).all()

    points = []
    for entity, laporan in rows:
        bencana = next(
            (
                e.nilai_teks
                for e in laporan.entitas
                if e.jenis_entitas == "Disaster"
            ),
            "",
        )
        points.append(
            MapPoint(
                id_laporan=laporan.id_laporan,
                jenis_entitas=entity.jenis_entitas,
                nilai_teks=entity.nilai_teks,
                latitude=entity.latitude,
                longitude=entity.longitude,
                tanggal_lapor=laporan.tanggal_lapor,
                bencana=bencana,
                status_kasus=laporan.kasus.status_kasus if laporan.kasus else None,
            )
        )
    return points
