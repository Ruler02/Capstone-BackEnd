"""Skema API untuk laporan dan entitas NER."""

from datetime import datetime

from pydantic import BaseModel, Field


class EntityOut(BaseModel):
    id_entitas: int
    jenis_entitas: str
    nilai_teks: str
    latitude: float | None = None
    longitude: float | None = None
    posisi: tuple[int, int] = (0, 0)

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    konten_teks: str | None = None
    phone_pelapor: str | None = Field(default=None, description="Nomor WhatsApp pelapor")


class ReportAccepted(BaseModel):
    id_laporan: str
    status: str
    detail: str


class ReportStatus(BaseModel):
    id_laporan: str
    status_verifikasi: str
    status_proses: str
    pesan_gagal: str | None = None


class ReportDetail(BaseModel):
    id_laporan: str
    sumber_input: str
    konten_teks: str | None
    status_verifikasi: str
    status_proses: str
    tanggal_lapor: datetime
    entitas: list[EntityOut]


class MapPoint(BaseModel):
    id_laporan: str
    jenis_entitas: str
    nilai_teks: str
    latitude: float
    longitude: float
    tanggal_lapor: datetime
    bencana: str = ""
    status_kasus: str | None = None
