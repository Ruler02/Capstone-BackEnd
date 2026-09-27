"""Uji aturan bisnis Admin: verifikasi, edit terbatas, eskalasi, penutupan."""

from tests.conftest import auth_header, create_user

from app.models.kasus import Kasus
from app.models.laporan import Laporan
from app.models.penugasan import Penugasan
from app.models.penugasan_unit import PenugasanUnit


def _seed_report(db, laporan_id: str, status: str = "menunggu_verifikasi") -> Laporan:
    report = Laporan(
        id_laporan=laporan_id,
        sumber_input="teks",
        konten_teks="Banjir di Surabaya, lima warga mengungsi.",
        status_verifikasi=status,
        status_proses="selesai",
    )
    db.add(report)
    db.commit()
    return report


def test_admin_endpoints_require_admin(client, bpbd_user):
    headers = auth_header(client, bpbd_user.email)
    assert client.get("/api/v1/admin/reports").status_code == 401
    assert client.get("/api/v1/admin/reports", headers=headers).status_code == 403


def test_queue_and_detail(client, db_session, admin_headers):
    _seed_report(db_session, "LPR-ADMIN01")

    queue = client.get("/api/v1/admin/reports", headers=admin_headers)
    assert queue.status_code == 200
    assert any(item["id_laporan"] == "LPR-ADMIN01" for item in queue.json())

    detail = client.get("/api/v1/admin/reports/LPR-ADMIN01", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["konten_teks"].startswith("Banjir")


def test_verify_flow(client, db_session, admin_headers, admin_user):
    _seed_report(db_session, "LPR-ADMIN02")

    ok = client.post(
        "/api/v1/admin/reports/LPR-ADMIN02/verify",
        headers=admin_headers,
        json={"keputusan": "verified"},
    )
    assert ok.status_code == 200
    assert db_session.get(Laporan, "LPR-ADMIN02").status_verifikasi == "terverifikasi"
    assert db_session.get(Laporan, "LPR-ADMIN02").id_admin_verifikator == admin_user.id_user

    again = client.post(
        "/api/v1/admin/reports/LPR-ADMIN02/verify",
        headers=admin_headers,
        json={"keputusan": "rejected"},
    )
    assert again.status_code == 409


def test_edit_only_allows_date_location_disaster(client, db_session, admin_headers):
    from app.models.entitas import EntitasNer

    _seed_report(db_session, "LPR-ADMIN03")
    person = EntitasNer(
        id_laporan="LPR-ADMIN03", jenis_entitas="Person", nilai_teks="warga"
    )
    db_session.add(person)
    db_session.commit()

    blocked = client.patch(
        "/api/v1/admin/reports/LPR-ADMIN03",
        headers=admin_headers,
        json={"entitas": [{"id_entitas": person.id_entitas, "jenis_entitas": "Person", "nilai_teks": "seseorang"}]},
    )
    assert blocked.status_code == 400

    allowed = client.patch(
        "/api/v1/admin/reports/LPR-ADMIN03",
        headers=admin_headers,
        json={"konten_teks": "Teks hasil koreksi admin."},
    )
    assert allowed.status_code == 200
    assert db_session.get(Laporan, "LPR-ADMIN03").konten_teks == "Teks hasil koreksi admin."


def test_escalate_requires_verified_and_single_case(client, db_session, admin_headers):
    _seed_report(db_session, "LPR-ADMIN04", status="menunggu_verifikasi")
    first = client.post(
        "/api/v1/admin/cases",
        headers=admin_headers,
        json={"id_laporan": "LPR-ADMIN04", "tingkat_urgensi": "darurat"},
    )
    assert first.status_code == 409

    _seed_report(db_session, "LPR-ADMIN05", status="terverifikasi")
    created = client.post(
        "/api/v1/admin/cases",
        headers=admin_headers,
        json={"id_laporan": "LPR-ADMIN05", "tingkat_urgensi": "darurat"},
    )
    assert created.status_code == 200
    assert created.json()["status_kasus"] == "menunggu_penugasan"

    duplicate = client.post(
        "/api/v1/admin/cases",
        headers=admin_headers,
        json={"id_laporan": "LPR-ADMIN05", "tingkat_urgensi": "tinggi"},
    )
    assert duplicate.status_code == 409


def test_closure_needs_all_units_completed(client, db_session, admin_headers, bpbd_user, admin_user):
    _seed_report(db_session, "LPR-ADMIN06", status="terverifikasi")
    case = Kasus(
        id_laporan="LPR-ADMIN06",
        tingkat_urgensi="tinggi",
        id_admin_eskalasi=admin_user.id_user,
        status_kasus="on_progress",
    )
    db_session.add(case)
    db_session.flush()
    task = Penugasan(id_kasus=case.id_kasus, id_pimpinan=admin_user.id_user, instruksi="Bersihkan")
    db_session.add(task)
    db_session.flush()
    db_session.add(PenugasanUnit(id_penugasan=task.id_penugasan, id_bpbd=bpbd_user.id_user))
    db_session.commit()

    early = client.post(
        f"/api/v1/admin/tasks/{task.id_penugasan}/verify-closure",
        headers=admin_headers,
        json={"keputusan": "disetujui"},
    )
    assert early.status_code == 400

    unit = db_session.get(
        PenugasanUnit, (task.id_penugasan, bpbd_user.id_user)
    )
    unit.status_tugas = "completed"
    db_session.commit()

    ok = client.post(
        f"/api/v1/admin/tasks/{task.id_penugasan}/verify-closure",
        headers=admin_headers,
        json={"keputusan": "disetujui"},
    )
    assert ok.status_code == 200
    assert db_session.get(Kasus, case.id_kasus).status_kasus == "selesai"


def test_rejected_closure_returns_units_to_on_progress(
    client, db_session, admin_headers, bpbd_user, admin_user
):
    _seed_report(db_session, "LPR-ADMIN07", status="terverifikasi")
    case = Kasus(
        id_laporan="LPR-ADMIN07",
        tingkat_urgensi="sedang",
        id_admin_eskalasi=admin_user.id_user,
        status_kasus="completed",
    )
    db_session.add(case)
    db_session.flush()
    task = Penugasan(id_kasus=case.id_kasus, id_pimpinan=admin_user.id_user, instruksi="X")
    db_session.add(task)
    db_session.flush()
    db_session.add(
        PenugasanUnit(
            id_penugasan=task.id_penugasan,
            id_bpbd=bpbd_user.id_user,
            status_tugas="completed",
        )
    )
    db_session.commit()

    missing_note = client.post(
        f"/api/v1/admin/tasks/{task.id_penugasan}/verify-closure",
        headers=admin_headers,
        json={"keputusan": "ditolak"},
    )
    assert missing_note.status_code == 400

    rejected = client.post(
        f"/api/v1/admin/tasks/{task.id_penugasan}/verify-closure",
        headers=admin_headers,
        json={"keputusan": "ditolak", "catatan": "Foto blur"},
    )
    assert rejected.status_code == 200
    unit = db_session.get(PenugasanUnit, (task.id_penugasan, bpbd_user.id_user))
    assert unit.status_tugas == "on_progress"
    assert db_session.get(Kasus, case.id_kasus).status_kasus == "on_progress"
