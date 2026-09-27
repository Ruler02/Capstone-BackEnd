"""Model pengguna: satu tabel untuk Admin, Pimpinan, dan Tim BPBD.

Dipisah lewat kolom `role` sesuai ERD. `instansi_daerah` hanya diisi
untuk role bpbd; role lain bernilai NULL.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id_user: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    instansi_daerah: Mapped[str | None] = mapped_column(String(120), default=None)
