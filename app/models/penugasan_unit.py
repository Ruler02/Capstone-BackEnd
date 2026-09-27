"""Tabel penghubung many-to-many: satu penugasan × satu unit BPBD.

Membawa status kerja tiap unit (assigned/on_progress/completed) — kolom
inilah yang diperbarui saat fitur "update status tugas" dipakai.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PenugasanUnit(Base):
    __tablename__ = "penugasan_unit"

    id_penugasan: Mapped[int] = mapped_column(
        ForeignKey("penugasan.id_penugasan"), primary_key=True
    )
    id_bpbd: Mapped[int] = mapped_column(ForeignKey("users.id_user"), primary_key=True)
    status_tugas: Mapped[str] = mapped_column(String(20), default="assigned")
    tanggal_update: Mapped[datetime] = mapped_column(server_default=func.now())

    penugasan = relationship("Penugasan", back_populates="units")
