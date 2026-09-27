"""Endpoint publik: lapor cepat, cek status, dan peta kejadian."""

from app.models.laporan import Laporan


def test_create_text_report_returns_202_with_public_id(client, db_session):
    response = client.post(
        "/api/v1/public/reports",
        data={
            "konten_teks": "Banjir di Surabaya.",
            "phone_pelapor": "081234567890",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["id_laporan"].startswith("LPR-")
    assert body["status"] == "diproses"

    saved = db_session.get(Laporan, body["id_laporan"])
    assert saved is not None
    assert saved.sumber_input == "teks"


def test_create_report_without_content_400(client):
    response = client.post("/api/v1/public/reports", data={})
    assert response.status_code == 400


def test_create_audio_report_rejects_wrong_format(client):
    response = client.post(
        "/api/v1/public/reports",
        files={"audio_file": ("foto.jpg", b"abc", "image/jpeg")},
    )
    assert response.status_code == 400


def test_status_unknown_id_404(client):
    assert client.get("/api/v1/public/reports/LPR-XXXXXXX0/status").status_code == 404


def test_status_returns_verification_state(client, db_session):
    db_session.add(
        Laporan(id_laporan="LPR-STATUS1", sumber_input="teks", konten_teks="halo")
    )
    db_session.commit()

    response = client.get("/api/v1/public/reports/LPR-STATUS1/status")
    assert response.status_code == 200
    assert response.json()["status_verifikasi"] == "menunggu_verifikasi"


def test_map_contains_only_verified_reports(client, db_session):
    from app.models.entitas import EntitasNer

    db_session.add(
        Laporan(
            id_laporan="LPR-MAPVER1",
            sumber_input="teks",
            konten_teks="x",
            status_verifikasi="terverifikasi",
        )
    )
    db_session.add(
        Laporan(
            id_laporan="LPR-MAPUNVR1",
            sumber_input="teks",
            konten_teks="x",
            status_verifikasi="menunggu_verifikasi",
        )
    )
    db_session.add(
        EntitasNer(
            id_laporan="LPR-MAPVER1",
            jenis_entitas="Location",
            nilai_teks="Surabaya",
            latitude=-7.25,
            longitude=112.75,
        )
    )
    db_session.add(
        EntitasNer(
            id_laporan="LPR-MAPUNVR1",
            jenis_entitas="Location",
            nilai_teks="Sidoarjo",
            latitude=-7.44,
            longitude=112.71,
        )
    )
    db_session.commit()

    points = client.get("/api/v1/public/map/incidents").json()
    ids = {p["id_laporan"] for p in points}
    assert ids == {"LPR-MAPVER1"}
