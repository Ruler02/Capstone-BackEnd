"""Skema API Pimpinan: dashboard agregat, penugasan, pantau progres."""

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    total_kejadian: int
    total_wilayah_terdampak: int
    kasus_ditangani: int
    kasus_belum_ditangani: int
    rekap_bulanan: list[dict]
    laporan_terkini: list[dict] = []
    kasus_terkini: list[dict] = []


class CreateAssignment(BaseModel):
    id_kasus: int
    instruksi: str = Field(min_length=3)
    id_bpbd: list[int] = Field(min_length=1)


class UnitProgress(BaseModel):
    id_bpbd: int
    nama: str
    status_tugas: str
    tanggal_update: datetime


class FieldReportOut(BaseModel):
    id_laporan_lapangan: int
    id_bpbd: int
    deskripsi: str
    status_saat_update: str
    waktu_update: datetime


class TaskProgress(BaseModel):
    id_penugasan: int
    id_kasus: int
    status_kasus: str
    instruksi: str
    units: list[UnitProgress]
    riwayat: list[FieldReportOut]
    bencana: str = ""
    lokasi: str = ""
