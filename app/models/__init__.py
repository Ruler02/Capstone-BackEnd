"""Impor seluruh model supaya terdaftar di Base.metadata untuk migrasi."""

from app.models.entitas import EntitasNer
from app.models.kasus import Kasus
from app.models.laporan import Laporan
from app.models.laporan_lapangan import LaporanLapangan
from app.models.penugasan import Penugasan
from app.models.penugasan_unit import PenugasanUnit
from app.models.user import User
from app.models.verifikasi_penutupan import VerifikasiPenutupan

__all__ = [
    "User",
    "Laporan",
    "EntitasNer",
    "Kasus",
    "Penugasan",
    "PenugasanUnit",
    "LaporanLapangan",
    "VerifikasiPenutupan",
]
