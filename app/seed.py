"""Seed akun demo untuk development.

Production sebaiknya mengganti password setelah deploy dan tidak memakai akun
contoh ini untuk data nyata. Tidak ada endpoint registrasi publik sesuai proposal.
"""

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import User

DEMO_USERS = [
    {"nama": "Admin BNPB", "email": "admin@sigap.id", "role": "admin", "instansi_daerah": None},
    {"nama": "Pimpinan BNPB", "email": "pimpinan@sigap.id", "role": "pimpinan", "instansi_daerah": None},
    {"nama": "Tim BPBD Surabaya", "email": "bpbd.surabaya@sigap.id", "role": "bpbd", "instansi_daerah": "BPBD Surabaya"},
    {"nama": "Tim BPBD Malang", "email": "bpbd.malang@sigap.id", "role": "bpbd", "instansi_daerah": "BPBD Malang"},
]


def seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for data in DEMO_USERS:
            if db.scalar(select(User).where(User.email == data["email"])) is None:
                db.add(User(**data, password_hash=hash_password("ubah-password-ini")))
        db.commit()
    print("Seed akun SIGAP selesai. Password demo: ubah-password-ini")


if __name__ == "__main__":
    seed()
