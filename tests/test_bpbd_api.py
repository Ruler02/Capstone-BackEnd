"""Uji alur penugasan Pimpinan → update tugas/laporan Tim BPBD."""

from tests.conftest import auth_header, create_user

from app.models.kasus import Kasus
from app.models.laporan import Laporan
from app.models.penugasan import Penugasan
from app.models.penugasan_unit import PenugasanUnit


def _seed_case(db, admin_id: int, status="menunggu_penugasan"):
    db.add(
        Laporan(
            id_laporan="LPR-PROGRESS1",
            sumber_input="teks",
            konten_teks="Banjir",
            status_verifikasi="terverifikasi",
            status_proses="selesai",
        )
    )
    db.flush()
    case = Kasus(
        id_laporan="LPR-PROGRESS1",
        tingkat_urgensi="tinggi",
        id_admin_eskalasi=admin_id,
        status_kasus=status,
    )
    db.add(case)
    db.commit()
    return case


def test_pimpinan_creates_assignment(client, db_session, pimpinan_user, bpbd_user):
    case = _seed_case(db_session, pimpinan_user.id_user)
    headers = auth_header(client, pimpinan_user.email)

    response = client.post(
        "/api/v1/pimpinan/penugasan",
        headers=headers,
        json={
            "id_kasus": case.id_kasus,
            "instruksi": "Evakuasi warga terdampak",
            "id_bpbd": [bpbd_user.id_user],
        },
    )
    assert response.status_code == 201
    task_id = response.json()["id_penugasan"]
    task = db_session.get(Penugasan, task_id)
    assert task is not None
    assert db_session.get(Kasus, case.id_kasus).status_kasus == "assigned"
    unit = db_session.get(PenugasanUnit, (task_id, bpbd_user.id_user))
    assert unit.status_tugas == "assigned"


def test_pimpinan_rejects_duplicate_assignment(client, db_session, pimpinan_user, bpbd_user):
    case = _seed_case(db_session, pimpinan_user.id_user)
    case.status_kasus = "assigned"
    db_session.commit()
    response = client.post(
        "/api/v1/pimpinan/penugasan",
        headers=auth_header(client, pimpinan_user.email),
        json={"id_kasus": case.id_kasus, "instruksi": "Instruksi cadangan", "id_bpbd": [bpbd_user.id_user]},
    )
    assert response.status_code == 409


def test_pimpinan_rejects_non_bpbd_target(client, db_session, pimpinan_user, admin_user):
    case = _seed_case(db_session, pimpinan_user.id_user)
    response = client.post(
        "/api/v1/pimpinan/penugasan",
        headers=auth_header(client, pimpinan_user.email),
        json={"id_kasus": case.id_kasus, "instruksi": "Instruksi lapangan", "id_bpbd": [admin_user.id_user]},
    )
    assert response.status_code == 400


def test_bpbd_scope_and_status_transitions(client, db_session, pimpinan_user, bpbd_user):
    other_bpbd = create_user(db_session, "bpbd", "other@sigap.id", "BPBD Malang")
    case = _seed_case(db_session, pimpinan_user.id_user)
    task = Penugasan(id_kasus=case.id_kasus, id_pimpinan=pimpinan_user.id_user, instruksi="X")
    db_session.add(task)
    db_session.flush()
    db_session.add(PenugasanUnit(id_penugasan=task.id_penugasan, id_bpbd=bpbd_user.id_user))
    db_session.commit()

    other_response = client.get(
        f"/api/v1/bpbd/tasks/{task.id_penugasan}",
        headers=auth_header(client, other_bpbd.email),
    )
    assert other_response.status_code == 404

    headers = auth_header(client, bpbd_user.email)
    on_progress = client.patch(
        f"/api/v1/bpbd/tasks/{task.id_penugasan}/status",
        headers=headers,
        json={"status_tugas": "on_progress"},
    )
    assert on_progress.status_code == 200

    invalid = client.patch(
        f"/api/v1/bpbd/tasks/{task.id_penugasan}/status",
        headers=headers,
        json={"status_tugas": "on_progress"},
    )
    assert invalid.status_code == 409

    completed = client.patch(
        f"/api/v1/bpbd/tasks/{task.id_penugasan}/status",
        headers=headers,
        json={"status_tugas": "completed"},
    )
    assert completed.status_code == 200
    assert db_session.get(Kasus, case.id_kasus).status_kasus == "completed"


def test_bpbd_field_report_requires_photo_for_completed(
    client, db_session, pimpinan_user, bpbd_user
):
    case = _seed_case(db_session, pimpinan_user.id_user)
    task = Penugasan(id_kasus=case.id_kasus, id_pimpinan=pimpinan_user.id_user, instruksi="X")
    db_session.add(task)
    db_session.flush()
    db_session.add(PenugasanUnit(id_penugasan=task.id_penugasan, id_bpbd=bpbd_user.id_user))
    db_session.commit()
    response = client.post(
        f"/api/v1/bpbd/tasks/{task.id_penugasan}/field-reports",
        headers=auth_header(client, bpbd_user.email),
        data={"deskripsi": "Selesai", "status_saat_update": "completed"},
    )
    assert response.status_code == 400
