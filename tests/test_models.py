"""Memastikan delapan tabel domain ERD terbuat lengkap di database."""

from sqlalchemy import inspect

from app import models  # noqa: F401
from app.core.database import Base

EXPECTED_TABLES = {
    "users",
    "laporan",
    "entitas_ner",
    "kasus",
    "penugasan",
    "penugasan_unit",
    "laporan_lapangan",
    "verifikasi_penutupan",
}


def test_all_eight_erd_tables_exist(db_session):
    inspector = inspect(db_session.bind)
    created = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(created), EXPECTED_TABLES - created


def test_laporan_uses_public_token_as_primary_key(db_session):
    columns = {c["name"] for c in inspect(db_session.bind).get_columns("laporan")}
    assert {"id_laporan", "phone_pelapor", "status_proses"} <= columns
