"""Endpoint Pimpinan: dashboard monitoring, penugasan, pantau progres."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import engine, get_db
from app.core.deps import require_role
from app.models.entitas import EntitasNer
from app.models.kasus import Kasus
from app.models.laporan import Laporan
from app.models.laporan_lapangan import LaporanLapangan
from app.models.penugasan import Penugasan
from app.models.penugasan_unit import PenugasanUnit
from app.models.user import User
from app.models.verifikasi_penutupan import VerifikasiPenutupan
from app.schemas.admin import CaseOut
from app.schemas.pimpinan import (
    CreateAssignment,
    DashboardStats,
    FieldReportOut,
    TaskProgress,
    UnitProgress,
)
from app.services.summary import bencana_dan_lokasi

router = APIRouter(prefix="/api/v1/pimpinan", tags=["pimpinan"])
pimpinan_only = Depends(require_role("pimpinan"))

HANDLED_STATUSES = ("completed", "selesai")

# SQLite memakai strftime, Postgres memakai to_char — pilih berdasarkan dialek
# supaya keduanya tetap bekerja.
if engine.dialect.name == "postgresql":
    kasus_bulan = func.to_char(Kasus.tanggal_eskalasi, "YYYY-MM")
else:
    kasus_bulan = func.strftime("%Y-%m", Kasus.tanggal_eskalasi)


@router.get("/dashboard", response_model=DashboardStats, dependencies=[pimpinan_only])
def dashboard(db: Session = Depends(get_db)) -> DashboardStats:
    total_cases = db.scalar(select(func.count(Kasus.id_kasus))) or 0
    handled = (
        db.scalar(
            select(func.count(Kasus.id_kasus)).where(
                Kasus.status_kasus.in_(HANDLED_STATUSES)
            )
        )
        or 0
    )
    from app.models.entitas import EntitasNer as E

    wilayah = db.scalar(
        select(func.count(func.distinct(E.nilai_teks))).where(
            E.jenis_entitas == "Location"
        )
    ) or 0

    per_month = db.execute(
        select(
            kasus_bulan.label("bulan"),
            func.count(Kasus.id_kasus),
        )
        .group_by("bulan")
        .order_by("bulan")
    ).all()

    reports = db.scalars(
        select(Laporan).options(selectinload(Laporan.entitas)).limit(6)
    ).all()
    cases = (
        db.scalars(
            select(Kasus)
            .options(selectinload(Kasus.laporan).selectinload(Laporan.entitas))
            .order_by(Kasus.tanggal_eskalasi.desc())
            .limit(6)
        )
        .all()
    )

    laporan_terkini = []
    for report in reports:
        bencana, lokasi = bencana_dan_lokasi(list(report.entitas))
        laporan_terkini.append(
            {
                "id_laporan": report.id_laporan,
                "bencana": bencana or "-",
                "lokasi": lokasi or "-",
                "status_verifikasi": report.status_verifikasi,
                "tanggal_lapor": report.tanggal_lapor,
            }
        )

    kasus_terkini = []
    for case in cases:
        bencana, lokasi = bencana_dan_lokasi(list(case.laporan.entitas))
        kasus_terkini.append(
            {
                "id_kasus": case.id_kasus,
                "id_laporan": case.id_laporan,
                "bencana": bencana or "-",
                "lokasi": lokasi or "-",
                "tingkat_urgensi": case.tingkat_urgensi,
                "status_kasus": case.status_kasus,
                "tanggal_eskalasi": case.tanggal_eskalasi,
            }
        )

    return DashboardStats(
        total_kejadian=total_cases,
        total_wilayah_terdampak=wilayah,
        kasus_ditangani=handled,
        kasus_belum_ditangani=total_cases - handled,
        rekap_bulanan=[{"bulan": bulan, "jumlah": jumlah} for bulan, jumlah in per_month],
        laporan_terkini=laporan_terkini,
        kasus_terkini=kasus_terkini,
    )


@router.get("/cases", response_model=list[CaseOut], dependencies=[pimpinan_only])
def list_cases_for_assignment(db: Session = Depends(get_db)) -> list[CaseOut]:
    cases = db.scalars(
        select(Kasus)
        .options(selectinload(Kasus.laporan).selectinload(Laporan.entitas))
        .where(Kasus.status_kasus == "menunggu_penugasan")
        .order_by(Kasus.tanggal_eskalasi.desc())
    ).all()
    results = []
    for case in cases:
        bencana, lokasi = bencana_dan_lokasi(list(case.laporan.entitas))
        results.append(
            CaseOut(
                id_kasus=case.id_kasus,
                id_laporan=case.id_laporan,
                tingkat_urgensi=case.tingkat_urgensi,
                status_kasus=case.status_kasus,
                tanggal_eskalasi=case.tanggal_eskalasi,
                bencana=bencana,
                lokasi=lokasi,
                status_verifikasi=case.laporan.status_verifikasi,
            )
        )
    return results


@router.get("/units", dependencies=[pimpinan_only])
def list_bpbd_units(db: Session = Depends(get_db)):
    units = db.scalars(
        select(User).where(User.role == "bpbd").order_by(User.nama)
    ).all()
    return [
        {"id_user": user.id_user, "nama": user.nama, "instansi_daerah": user.instansi_daerah}
        for user in units
    ]


@router.post("/penugasan", status_code=201, dependencies=[pimpinan_only])
def create_assignment(
    body: CreateAssignment,
    pimpinan: User = Depends(require_role("pimpinan")),
    db: Session = Depends(get_db),
):
    case = db.get(Kasus, body.id_kasus)
    if case is None:
        raise HTTPException(404, detail="Kasus tidak ditemukan")
    if case.status_kasus != "menunggu_penugasan":
        raise HTTPException(409, detail="Kasus sudah memiliki penugasan atau status tidak sah")

    units = db.scalars(select(User).where(User.id_user.in_(body.id_bpbd))).all()
    if len(units) != len(set(body.id_bpbd)):
        raise HTTPException(400, detail="Ada id_bpbd yang tidak ditemukan")
    if any(u.role != "bpbd" for u in units):
        raise HTTPException(400, detail="Semua id_bpbd harus berrole bpbd")

    task = Penugasan(
        id_kasus=case.id_kasus,
        id_pimpinan=pimpinan.id_user,
        instruksi=body.instruksi,
    )
    db.add(task)
    db.flush()
    for unit in units:
        db.add(
            PenugasanUnit(
                id_penugasan=task.id_penugasan, id_bpbd=unit.id_user, status_tugas="assigned"
            )
        )
    case.status_kasus = "assigned"
    db.commit()
    return {"id_penugasan": task.id_penugasan, "id_kasus": case.id_kasus}


@router.get("/tasks/progress", response_model=list[TaskProgress], dependencies=[pimpinan_only])
def progress(db: Session = Depends(get_db)) -> list[TaskProgress]:
    tasks = db.scalars(
        select(Penugasan).options(
            selectinload(Penugasan.units),
            selectinload(Penugasan.laporan_lapangan),
            selectinload(Penugasan.kasus),
        )
    ).all()
    results = []
    for task in tasks:
        unit_ids = [u.id_bpbd for u in task.units]
        names = {}
        if unit_ids:
            for user in db.scalars(select(User).where(User.id_user.in_(unit_ids))):
                names[user.id_user] = user.nama

        entities = db.scalars(
            select(EntitasNer).where(EntitasNer.id_laporan == task.kasus.id_laporan)
        ).all()
        bencana, lokasi = bencana_dan_lokasi(list(entities))

        results.append(
            TaskProgress(
                id_penugasan=task.id_penugasan,
                id_kasus=task.id_kasus,
                status_kasus=task.kasus.status_kasus,
                instruksi=task.instruksi,
                bencana=bencana,
                lokasi=lokasi,
                units=[
                    UnitProgress(
                        id_bpbd=u.id_bpbd,
                        nama=names.get(u.id_bpbd, "-"),
                        status_tugas=u.status_tugas,
                        tanggal_update=u.tanggal_update,
                    )
                    for u in task.units
                ],
                riwayat=[
                    FieldReportOut(
                        id_laporan_lapangan=r.id_laporan_lapangan,
                        id_bpbd=r.id_bpbd,
                        deskripsi=r.deskripsi,
                        status_saat_update=r.status_saat_update,
                        waktu_update=r.waktu_update,
                    )
                    for r in sorted(task.laporan_lapangan, key=lambda x: x.waktu_update)
                ],
            )
        )
    return results
