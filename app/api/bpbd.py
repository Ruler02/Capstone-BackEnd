"""Endpoint Tim BPBD: hanya mengakses unit penugasan miliknya sendiri."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_role
from app.models.kasus import Kasus
from app.models.laporan_lapangan import LaporanLapangan
from app.models.penugasan import Penugasan
from app.models.penugasan_unit import PenugasanUnit
from app.models.user import User
from app.schemas.bpbd import BpbdTaskOut, FieldReportOut, TaskDetail, TaskStatusUpdate
from app.services.storage import build_storage

router = APIRouter(prefix="/api/v1/bpbd", tags=["bpbd"])
bpbd_only = Depends(require_role("bpbd"))
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PHOTO_BYTES = 10 * 1024 * 1024


def _unit(db: Session, id_penugasan: int, user_id: int) -> PenugasanUnit:
    unit = db.get(PenugasanUnit, (id_penugasan, user_id))
    if unit is None:
        raise HTTPException(404, detail="Penugasan tidak ditemukan untuk unit ini")
    return unit


@router.get("/tasks", response_model=list[BpbdTaskOut], dependencies=[bpbd_only])
def list_tasks(user: User = Depends(require_role("bpbd")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(PenugasanUnit, Penugasan)
        .join(Penugasan, PenugasanUnit.id_penugasan == Penugasan.id_penugasan)
        .where(PenugasanUnit.id_bpbd == user.id_user)
    ).all()
    return [
        BpbdTaskOut(
            id_penugasan=unit.id_penugasan,
            id_kasus=task.id_kasus,
            instruksi=task.instruksi,
            status_tugas=unit.status_tugas,
            tanggal_update=unit.tanggal_update,
        )
        for unit, task in rows
    ]


@router.get("/tasks/{id_penugasan}", response_model=TaskDetail, dependencies=[bpbd_only])
def get_task(
    id_penugasan: int,
    user: User = Depends(require_role("bpbd")),
    db: Session = Depends(get_db),
):
    unit = _unit(db, id_penugasan, user.id_user)
    task = db.get(Penugasan, id_penugasan)
    reports = db.scalars(
        select(LaporanLapangan).where(LaporanLapangan.id_penugasan == id_penugasan)
    ).all()
    return TaskDetail(
        id_penugasan=task.id_penugasan,
        id_kasus=task.id_kasus,
        instruksi=task.instruksi,
        status_tugas=unit.status_tugas,
        tanggal_update=unit.tanggal_update,
        status_kasus=task.kasus.status_kasus,
        laporan=[
            FieldReportOut(
                id_laporan_lapangan=r.id_laporan_lapangan,
                id_penugasan=r.id_penugasan,
                deskripsi=r.deskripsi,
                foto_path=r.foto_path,
                status_saat_update=r.status_saat_update,
                waktu_update=r.waktu_update,
            )
            for r in reports
        ],
    )


@router.patch("/tasks/{id_penugasan}/status", dependencies=[bpbd_only])
def update_status(
    id_penugasan: int,
    body: TaskStatusUpdate,
    user: User = Depends(require_role("bpbd")),
    db: Session = Depends(get_db),
):
    unit = _unit(db, id_penugasan, user.id_user)
    valid = {"assigned": {"on_progress"}, "on_progress": {"completed"}}
    if body.status_tugas not in valid.get(unit.status_tugas, set()):
        raise HTTPException(409, detail="Transisi status tugas tidak valid")
    unit.status_tugas = body.status_tugas
    all_units = db.scalars(
        select(PenugasanUnit).where(PenugasanUnit.id_penugasan == id_penugasan)
    ).all()
    case = db.get(Penugasan, id_penugasan).kasus
    if body.status_tugas == "on_progress":
        case.status_kasus = "on_progress"
    elif all_units and all(u.status_tugas == "completed" for u in all_units):
        case.status_kasus = "completed"
    db.commit()
    return {"id_penugasan": id_penugasan, "status_tugas": unit.status_tugas}


@router.post("/tasks/{id_penugasan}/field-reports", response_model=FieldReportOut, dependencies=[bpbd_only])
async def create_field_report(
    id_penugasan: int,
    deskripsi: str = Form(...),
    status_saat_update: str = Form(...),
    foto_file: UploadFile | None = File(default=None),
    user: User = Depends(require_role("bpbd")),
    db: Session = Depends(get_db),
):
    unit = _unit(db, id_penugasan, user.id_user)
    if status_saat_update not in {"assigned", "on_progress", "completed"}:
        raise HTTPException(400, detail="Status laporan lapangan tidak valid")
    if status_saat_update == "completed" and foto_file is None:
        raise HTTPException(400, detail="Bukti foto wajib saat status completed")

    photo_path = None
    if foto_file is not None:
        filename = (foto_file.filename or "").lower()
        if not any(filename.endswith(ext) for ext in ALLOWED_PHOTO_EXTENSIONS):
            raise HTTPException(400, detail="Format foto tidak didukung")
        data = await foto_file.read()
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(413, detail="Ukuran foto maksimal 10MB")
        photo_path = build_storage(get_settings()).save(data, foto_file.filename or "foto", "photos")

    report = LaporanLapangan(
        id_penugasan=id_penugasan,
        id_bpbd=user.id_user,
        deskripsi=deskripsi,
        foto_path=photo_path,
        status_saat_update=status_saat_update,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
