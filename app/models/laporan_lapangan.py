"""Laporan kondisi lapangan dari Tim BPBD: narasi + foto bukti.

`foto_path` diverifikasi Admin saat status sudah completed sebelum kasus
bisa ditutup.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LaporanLapangan(Base):
    __tablename__ = "laporan_lapangan"

    id_laporan_lapangan: Mapped[int] = mapped_column(primary_key=True)
    id_penugasan: Mapped[int] = mapped_column(ForeignKey("penugasan.id_penugasan"), index=True)
    id_bpbd: Mapped[int] = mapped_column(ForeignKey("users.id_user"))
    deskripsi: Mapped[str] = mapped_column(Text)
    foto_path: Mapped[str | None] = mapped_column(String(500), default=None)
    status_saat_update: Mapped[str] = mapped_column(String(20))
    waktu_update: Mapped[datetime] = mapped_column(server_default=func.now())

    penugasan = relationship("Penugasan", back_populates="laporan_lapangan")
