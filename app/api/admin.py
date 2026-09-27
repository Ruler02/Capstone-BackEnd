"""Endpoint Admin sesuai flowchart verifikasi, eskalasi, dan penutupan."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_role
from app.models.entitas import EntitasNer
from app.models.kasus import Kasus
from app.models.laporan import Laporan
from app.models.penugasan import Penugasan
from app.models.user import User
from app.schemas.admin import (
    AdminReportDetail,
    AdminReportSummary,
    CaseOut,
    ClosureDecision,
    EscalateRequest,
    ReportPatch,
    TaskSummary,
    VerifyDecision,
)
from app.schemas.laporan import EntityOut
from app.services.closure import verify_closure
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
admin_only = Depends(require_role("admin"))


def _entity_out(entity: EntitasNer) -> EntityOut:
    return EntityOut(
        id_entitas=entity.id_entitas,
        jenis_entitas=entity.jenis_entitas,
        nilai_teks=entity.nilai_teks,
        latitude=entity.latitude,
        longitude=entity.longitude,
    )


@router.get("/reports", response_model=list[AdminReportSummary], dependencies=[admin_only])
def list_reports(status: str | None = None, db: Session = Depends(get_db)):
    query = select(Laporan).order_by(Laporan.tanggal_lapor.desc())
    if status:
        query = query.where(Laporan.status_verifikasi == status)
    reports = db.scalars(query).all()
    return [
        AdminReportSummary(
            id_laporan=r.id_laporan,
            sumber_input=r.sumber_input,
            status_verifikasi=r.status_verifikasi,
            status_proses=r.status_proses,
            tanggal_lapor=r.tanggal_lapor,
            cuplikan=(r.konten_teks or "")[:160],
        )
        for r in reports
    ]


@router.get("/reports/{id_laporan}", response_model=AdminReportDetail, dependencies=[admin_only])
def get_report(id_laporan: str, db: Session = Depends(get_db)):
    report = db.get(Laporan, id_laporan)
    if report is None:
        raise HTTPException(404, detail="Laporan tidak ditemukan")
    return AdminReportDetail(
        id_laporan=report.id_laporan,
        sumber_input=report.sumber_input,
        status_verifikasi=report.status_verifikasi,
        status_proses=report.status_proses,
        tanggal_lapor=report.tanggal_lapor,
        cuplikan=(report.konten_teks or "")[:160],
        konten_teks=report.konten_teks,
        phone_pelapor=report.phone_pelapor,
        pesan_gagal=report.pesan_gagal,
        entitas=[_entity_out(e) for e in report.entitas],
    )


@router.patch("/reports/{id_laporan}", response_model=AdminReportDetail, dependencies=[admin_only])
def edit_report(
    id_laporan: str,
    body: ReportPatch,
    db: Session = Depends(get_db),
):
    report = db.get(Laporan, id_laporan)
    if report is None:
        raise HTTPException(404, detail="Laporan tidak ditemukan")
    if body.konten_teks is not None:
        report.konten_teks = body.konten_teks
    if body.entitas is not None:
        allowed = {"Date", "Location", "Disaster"}
        if any(entity.jenis_entitas not in allowed for entity in body.entitas):
            raise HTTPException(400, detail="Edit hanya boleh untuk Date, Location, Disaster")
        for incoming in body.entitas:
            existing = db.get(EntitasNer, incoming.id_entitas)
            if existing is None or existing.id_laporan != id_laporan:
                raise HTTPException(404, detail="Entitas tidak ditemukan di laporan ini")
            existing.nilai_teks = incoming.nilai_teks
            existing.latitude = incoming.latitude
            existing.longitude = incoming.longitude
    db.commit()
    return get_report(id_laporan, db)


@router.post("/reports/{id_laporan}/verify", dependencies=[admin_only])
def verify_report(
    id_laporan: str,
    body: VerifyDecision,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    report = db.get(Laporan, id_laporan)
    if report is None:
        raise HTTPException(404, detail="Laporan tidak ditemukan")
    if report.status_verifikasi != "menunggu_verifikasi":
        raise HTTPException(409, detail="Laporan sudah diproses sebelumnya")
    report.status_verifikasi = "terverifikasi" if body.keputusan == "verified" else "ditolak"
    report.id_admin_verifikator = admin.id_user
    db.commit()
    return {"id_laporan": id_laporan, "status_verifikasi": report.status_verifikasi}


@router.post("/reports/{id_laporan}/reprocess", dependencies=[admin_only])
def reprocess_report(id_laporan: str, db: Session = Depends(get_db)):
    if db.get(Laporan, id_laporan) is None:
        raise HTTPException(404, detail="Laporan tidak ditemukan")
    run_pipeline(db, id_laporan)
    return {"id_laporan": id_laporan, "status_proses": "selesai"}


@router.get("/cases", response_model=list[CaseOut], dependencies=[admin_only])
def list_cases(db: Session = Depends(get_db)):
    return db.scalars(select(Kasus).order_by(Kasus.tanggal_eskalasi.desc())).all()


@router.post("/cases", response_model=CaseOut, dependencies=[admin_only])
def escalate_case(
    body: EscalateRequest,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    report = db.get(Laporan, body.id_laporan)
    if report is None:
        raise HTTPException(404, detail="Laporan tidak ditemukan")
    if report.status_verifikasi != "terverifikasi":
        raise HTTPException(409, detail="Hanya laporan terverifikasi yang dapat dieskalasi")
    if report.kasus is not None:
        raise HTTPException(409, detail="Laporan sudah menjadi kasus")
    case = Kasus(
        id_laporan=report.id_laporan,
        tingkat_urgensi=body.tingkat_urgensi,
        id_admin_eskalasi=admin.id_user,
        status_kasus="menunggu_penugasan",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/tasks", response_model=list[TaskSummary], dependencies=[admin_only])
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.scalars(select(Penugasan).options(selectinload(Penugasan.units))).all()
    return [
        TaskSummary(
            id_penugasan=t.id_penugasan,
            id_kasus=t.id_kasus,
            instruksi=t.instruksi,
            status_kasus=t.kasus.status_kasus,
            units=[
                {"id_bpbd": u.id_bpbd, "status_tugas": u.status_tugas}
                for u in t.units
            ],
        )
        for t in tasks
    ]


@router.post("/tasks/{id_penugasan}/verify-closure", dependencies=[admin_only])
def close_task(
    id_penugasan: int,
    body: ClosureDecision,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    result = verify_closure(db, id_penugasan, admin, body.keputusan, body.catatan)
    return {"id_verifikasi": result.id_verifikasi, "status_verifikasi": result.status_verifikasi}
