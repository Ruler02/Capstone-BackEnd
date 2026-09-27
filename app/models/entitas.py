"""Hasil ekstraksi NER per laporan. Satu laporan bisa punya banyak entitas.

Hanya empat kategori sesuai proposal: Person, Date, Location, Disaster.
`latitude`/`longitude` terisi hanya untuk Location setelah geocoding.
"""

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EntitasNer(Base):
    __tablename__ = "entitas_ner"

    id_entitas: Mapped[int] = mapped_column(primary_key=True)
    id_laporan: Mapped[str] = mapped_column(ForeignKey("laporan.id_laporan"), index=True)
    jenis_entitas: Mapped[str] = mapped_column(String(20))
    nilai_teks: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)

    laporan = relationship("Laporan", back_populates="entitas")
