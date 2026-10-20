"""Skema API Admin: antrian laporan, verifikasi, eskalasi, penutupan kasus."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.laporan import EntityOut


class AdminReportSummary(BaseModel):
    id_laporan: str
    sumber_input: str
    status_verifikasi: str
    status_proses: str
    tanggal_lapor: datetime
    cuplikan: str = ""
    bencana: str = ""
    lokasi: str = ""
    phone_pelapor: str | None = None

    model_config = {"from_attributes": True}


class AdminReportDetail(AdminReportSummary):
    konten_teks: str | None
    phone_pelapor: str | None
    pesan_gagal: str | None
    entitas: list[EntityOut]


class ReportPatch(BaseModel):
    konten_teks: str | None = None
    entitas: list[EntityOut] | None = Field(
        default=None,
        description="Edit hanya diizinkan untuk Date, Location, Disaster",
    )


class VerifyDecision(BaseModel):
    keputusan: str = Field(pattern="^(verified|rejected)$")


class EscalateRequest(BaseModel):
    id_laporan: str
    tingkat_urgensi: str = Field(pattern="^(rendah|sedang|tinggi|darurat)$")


class CaseOut(BaseModel):
    id_kasus: int
    id_laporan: str
    tingkat_urgensi: str
    status_kasus: str
    tanggal_eskalasi: datetime
    bencana: str = ""
    lokasi: str = ""
    status_verifikasi: str | None = None
    id_penugasan: int | None = None
    units: list[dict] = []
    penutupan_status: str | None = None
    nama_unit: str = ""

    model_config = {"from_attributes": True}


class TaskSummary(BaseModel):
    id_penugasan: int
    id_kasus: int
    instruksi: str
    status_kasus: str
    units: list[dict]
    bencana: str = ""
    lokasi: str = ""


class ClosureDecision(BaseModel):
    keputusan: str = Field(pattern="^(disetujui|ditolak)$")
    catatan: str | None = None
