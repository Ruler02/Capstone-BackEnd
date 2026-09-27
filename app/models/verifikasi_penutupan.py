"""Hasil pemeriksaan Admin terhadap bukti penyelesaian dari Tim BPBD.

Jika disetujui, kasus berubah menjadi selesai. Jika ditolak, `catatan`
wajib diisi sebagai acuan unit BPBD memperbaiki pekerjaan.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VerifikasiPenutupan(Base):
    __tablename__ = "verifikasi_penutupan"

    id_verifikasi: Mapped[int] = mapped_column(primary_key=True)
    id_penugasan: Mapped[int] = mapped_column(ForeignKey("penugasan.id_penugasan"))
    id_admin: Mapped[int] = mapped_column(ForeignKey("users.id_user"))
    status_verifikasi: Mapped[str] = mapped_column(String(20))
    catatan: Mapped[str | None] = mapped_column(Text, default=None)
    tanggal_verifikasi: Mapped[datetime] = mapped_column(server_default=func.now())
