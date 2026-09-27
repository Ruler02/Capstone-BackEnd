"""Laporan masuk dari pelapor (teks langsung atau audio hasil transkripsi).

`id_laporan` adalah token publik (mis. LPR-7F3KQ2ZM) yang dikirim ke pelapor
lewat WhatsApp untuk cek status — bukan autoincrement, supaya tidak bisa
ditebak oleh pihak lain.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Laporan(Base):
    __tablename__ = "laporan"

    id_laporan: Mapped[str] = mapped_column(String(16), primary_key=True)
    sumber_input: Mapped[str] = mapped_column(String(10))
    audio_path: Mapped[str | None] = mapped_column(String(500), default=None)
    konten_teks: Mapped[str | None] = mapped_column(Text, default=None)
    status_verifikasi: Mapped[str] = mapped_column(String(30), default="menunggu_verifikasi")
    tanggal_lapor: Mapped[datetime] = mapped_column(server_default=func.now())
    id_admin_verifikator: Mapped[int | None] = mapped_column(
        ForeignKey("users.id_user"), default=None
    )

    phone_pelapor: Mapped[str | None] = mapped_column(String(30), default=None)
    status_proses: Mapped[str] = mapped_column(String(20), default="diproses")
    pesan_gagal: Mapped[str | None] = mapped_column(Text, default=None)

    entitas = relationship("EntitasNer", back_populates="laporan", cascade="all, delete-orphan")
    kasus = relationship("Kasus", back_populates="laporan", uselist=False)
