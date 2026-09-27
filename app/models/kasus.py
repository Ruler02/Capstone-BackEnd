"""Kasus: laporan terverifikasi yang dieskalasi Admin.

Relasi LAPORAN-KASUS bersifat 0..1 (ERD): hanya laporan terverifikasi
dan mendesak yang menjadi kasus operasional.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Kasus(Base):
    __tablename__ = "kasus"

    id_kasus: Mapped[int] = mapped_column(primary_key=True)
    id_laporan: Mapped[str] = mapped_column(ForeignKey("laporan.id_laporan"), unique=True)
    tingkat_urgensi: Mapped[str] = mapped_column(String(20))
    id_admin_eskalasi: Mapped[int] = mapped_column(ForeignKey("users.id_user"))
    tanggal_eskalasi: Mapped[datetime] = mapped_column(server_default=func.now())
    status_kasus: Mapped[str] = mapped_column(String(30), default="menunggu_penugasan")

    laporan = relationship("Laporan", back_populates="kasus")
    penugasan = relationship("Penugasan", back_populates="kasus", uselist=False)
