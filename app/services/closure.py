"""Logika verifikasi penutupan kasus dari bukti lapangan Tim BPBD."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.kasus import Kasus
from app.models.penugasan import Penugasan
from app.models.penugasan_unit import PenugasanUnit
from app.models.user import User
from app.models.verifikasi_penutupan import VerifikasiPenutupan


def verify_closure(
    db: Session,
    id_penugasan: int,
    admin: User,
    keputusan: str,
    catatan: str | None,
) -> VerifikasiPenutupan:
    penugasan = db.get(Penugasan, id_penugasan)
    if penugasan is None:
        raise HTTPException(404, detail="Penugasan tidak ditemukan")

    units = (
        db.query(PenugasanUnit)
        .filter(PenugasanUnit.id_penugasan == id_penugasan)
        .all()
    )
    if not units or any(u.status_tugas != "completed" for u in units):
        raise HTTPException(
            400, detail="Penutupan hanya bisa diverifikasi setelah semua unit completed"
        )
    if keputusan == "ditolak" and not (catatan and catatan.strip()):
        raise HTTPException(400, detail="Catatan wajib diisi saat bukti ditolak")

    kasus = db.get(Kasus, penugasan.id_kasus)
    verifikasi = VerifikasiPenutupan(
        id_penugasan=id_penugasan,
        id_admin=admin.id_user,
        status_verifikasi=keputusan,
        catatan=catatan,
    )
    db.add(verifikasi)

    if keputusan == "disetujui":
        kasus.status_kasus = "selesai"
    else:
        for unit in units:
            unit.status_tugas = "on_progress"
            unit.tanggal_update = datetime.now(timezone.utc)
        kasus.status_kasus = "on_progress"

    db.commit()
    db.refresh(verifikasi)
    return verifikasi
