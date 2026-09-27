"""Penugasan: instruksi Pimpinan untuk sebuah kasus, diarahkan ke unit BPBD.

Satu kasus hanya punya satu penugasan aktif (`uselist=False`), tetapi satu
penugasan bisa menunjuk banyak unit lewat PENUGASAN_UNIT.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Penugasan(Base):
    __tablename__ = "penugasan"

    id_penugasan: Mapped[int] = mapped_column(primary_key=True)
    id_kasus: Mapped[int] = mapped_column(ForeignKey("kasus.id_kasus"))
    id_pimpinan: Mapped[int] = mapped_column(ForeignKey("users.id_user"))
    instruksi: Mapped[str] = mapped_column(Text)
    tanggal_penugasan: Mapped[datetime] = mapped_column(server_default=func.now())

    kasus = relationship("Kasus", back_populates="penugasan")
    units = relationship(
        "PenugasanUnit", back_populates="penugasan", cascade="all, delete-orphan"
    )
    laporan_lapangan = relationship(
        "LaporanLapangan", back_populates="penugasan", cascade="all, delete-orphan"
    )
