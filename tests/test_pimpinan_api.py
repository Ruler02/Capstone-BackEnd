"""Uji dashboard monitoring dan pantau progres milik Pimpinan."""

from datetime import datetime, timezone

from tests.conftest import auth_header

from app.models.entitas import EntitasNer
from app.models.kasus import Kasus
from app.models.laporan import Laporan
from app.models.laporan_lapangan import LaporanLapangan
from app.models.penugasan import Penugasan
from app.models.penugasan_unit import PenugasanUnit


def test_dashboard_aggregates_cases_and_wilayah(client, db_session, admin_user):
    db_session.add(
        Laporan(
            id_laporan="LPR-DASH01",
            sumber_input="teks",
            konten_teks="x",
            status_verifikasi="terverifikasi",
            status_proses="selesai",
        )
    )
    db_session.flush()
    db_session.add(
        Kasus(
            id_laporan="LPR-DASH01",
            tingkat_urgensi="tinggi",
            id_admin_eskalasi=admin_user.id_user,
            status_kasus="assigned",
        )
    )
    db_session.add(
        EntitasNer(
            id_laporan="LPR-DASH01",
            jenis_entitas="Location",
            nilai_teks="Surabaya",
            latitude=-7.2,
            longitude=112.7,
        )
    )
    db_session.commit()

    from tests.conftest import create_user

    pimpinan = create_user(db_session, "pimpinan", "p2@sigap.id")
    response = client.get(
        "/api/v1/pimpinan/dashboard", headers=auth_header(client, pimpinan.email)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_kejadian"] == 1
    assert body["kasus_belum_ditangani"] == 1
    assert body["total_wilayah_terdampak"] == 1


def test_progress_shows_units_and_field_history(client, db_session, admin_user):
    from tests.conftest import create_user

    pimpinan = create_user(db_session, "pimpinan", "p3@sigap.id")
    bpbd = create_user(db_session, "bpbd", "b3@sigap.id", "BPBD Surabaya")

    db_session.add(
        Laporan(
            id_laporan="LPR-PROG01",
            sumber_input="teks",
            konten_teks="x",
            status_verifikasi="terverifikasi",
            status_proses="selesai",
        )
    )
    db_session.flush()
    case = Kasus(
        id_laporan="LPR-PROG01",
        tingkat_urgensi="sedang",
        id_admin_eskalasi=admin_user.id_user,
        status_kasus="on_progress",
    )
    db_session.add(case)
    db_session.flush()
    task = Penugasan(id_kasus=case.id_kasus, id_pimpinan=pimpinan.id_user, instruksi="Cek lokasi")
    db_session.add(task)
    db_session.flush()
    db_session.add(
        PenugasanUnit(
            id_penugasan=task.id_penugasan, id_bpbd=bpbd.id_user, status_tugas="on_progress"
        )
    )
    db_session.add(
        LaporanLapangan(
            id_penugasan=task.id_penugasan,
            id_bpbd=bpbd.id_user,
            deskripsi="Genangan mulai surut",
            status_saat_update="on_progress",
            waktu_update=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/pimpinan/tasks/progress", headers=auth_header(client, pimpinan.email)
    )
    assert response.status_code == 200
    progress = response.json()[0]
    assert progress["status_kasus"] == "on_progress"
    assert progress["units"][0]["nama"] == "Pengguna bpbd"
    assert progress["riwayat"][0]["deskripsi"] == "Genangan mulai surut"


def test_pimpinan_endpoints_forbidden_for_admin(client, admin_headers):
    assert client.get("/api/v1/pimpinan/dashboard", headers=admin_headers).status_code == 403
