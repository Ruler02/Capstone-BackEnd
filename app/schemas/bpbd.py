"""Skema API Tim BPBD untuk tugas dan laporan lapangan."""

from datetime import datetime

from pydantic import BaseModel, Field


class BpbdTaskOut(BaseModel):
    id_penugasan: int
    id_kasus: int
    instruksi: str
    status_tugas: str
    tanggal_update: datetime
    bencana: str = ""
    lokasi: str = ""
    status_kasus: str = ""


class TaskStatusUpdate(BaseModel):
    status_tugas: str = Field(pattern="^(on_progress|completed)$")


class FieldReportOut(BaseModel):
    id_laporan_lapangan: int
    id_penugasan: int
    deskripsi: str
    foto_path: str | None
    status_saat_update: str
    waktu_update: datetime


class TaskDetail(BpbdTaskOut):
    status_kasus: str
    laporan: list[FieldReportOut]
