"""Seed data demo agar mockup terlihat hidup tanpa menunggu input manual.

Data dibuat mengikuti status lifecycle yang valid di backend:
LAPORAN -> KASUS -> PENUGASAN -> PENUGASAN_UNIT -> LAPORAN_LAPANGAN -> PENUTUPAN.

Idempoten: mengulang perintah ini tidak menggandakan data.
"""

from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import (
    EntitasNer,
    Kasus,
    Laporan,
    LaporanLapangan,
    Penugasan,
    PenugasanUnit,
    User,
    VerifikasiPenutupan,
)

NOW = datetime.now().replace(microsecond=0)

DEMO_LAPORAN = [
    {
        "id_laporan": "LPR-A1B2C3D4",
        "sumber": "teks",
        "ringkasan": "Banjir rob melanda pesisir Kenjeran Surabaya sejak dini hari.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "selesai",
        "phone": "081234567890",
        "hari_lalu": 0,
        "entitas": {
            "Person": "Warga Kenjeran",
            "Date": "9 Oktober 2026",
            "Location": "Kenjeran, Surabaya",
            "Disaster": "banjir rob",
        },
        "koordinat": (-7.2575, 112.7917),
    },
    {
        "id_laporan": "LPR-E5F6G7H8",
        "sumber": "teks",
        "ringkasan": "Tanah longsor menutup akses jalan di Kecamatan Pujon.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "selesai",
        "phone": "081399900111",
        "hari_lalu": 1,
        "entitas": {
            "Person": "Warga Pujon",
            "Date": "8 Oktober 2026",
            "Location": "Kecamatan Pujon, Kabupaten Malang",
            "Disaster": "tanah longsor",
        },
        "koordinat": (-7.9774, 112.4775),
    },
    {
        "id_laporan": "LPR-I9J0K1L2",
        "sumber": "teks",
        "ringkasan": "Luapan Kali Porong menggenangi pemukiman warga Sidoarjo.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "selesai",
        "phone": "081477700222",
        "hari_lalu": 1,
        "entitas": {
            "Person": "Warga Sidoarjo",
            "Date": "8 Oktober 2026",
            "Location": "Kecamatan Porong, Kabupaten Sidoarjo",
            "Disaster": "banjir luapan",
        },
        "koordinat": (-7.4478, 112.6933),
    },
    {
        "id_laporan": "LPR-M3N4O5P6",
        "sumber": "audio",
        "ringkasan": "Angin puting beliung merusak atap rumah di Sedati Sidoarjo.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081555500333",
        "hari_lalu": 2,
        "entitas": {
            "Person": "Rina Wijaya",
            "Date": "7 Oktober 2026",
            "Location": "Kecamatan Sedati, Kabupaten Sidoarjo",
            "Disaster": "angin puting beliung",
        },
        "koordinat": (-7.3964, 112.7219),
    },
    {
        "id_laporan": "LPR-Q7R8S9T0",
        "sumber": "teks",
        "ringkasan": "Kebakaran hutan di kawasan Tretes meningkat asap pekat.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081666600444",
        "hari_lalu": 3,
        "entitas": {
            "Person": "Tim Reaksi Cepat",
            "Date": "6 Oktober 2026",
            "Location": "Kecamatan Tretes, Kabupaten Pasuruan",
            "Disaster": "kebakaran hutan",
        },
        "koordinat": (-7.7469, 112.7036),
    },
    {
        "id_laporan": "LPR-U1V2W3X4",
        "sumber": "teks",
        "ringkasan": "Gempa bumi magnitudo 4.2 dirasakan warga Kota Batu.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081777700555",
        "hari_lalu": 4,
        "entitas": {
            "Person": "Warga Kota Batu",
            "Date": "5 Oktober 2026",
            "Location": "Kota Batu, Jawa Timur",
            "Disaster": "gempa bumi",
        },
        "koordinat": (-7.9070, 112.5190),
    },
    {
        "id_laporan": "LPR-Y5Z6A7B8",
        "sumber": "audio",
        "ringkasan": "Longsor susulan terjadi di jalur Lawang menuju Malang.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081888800666",
        "hari_lalu": 5,
        "entitas": {
            "Person": "Petugas Jalan Lawang",
            "Date": "4 Oktober 2026",
            "Location": "Kecamatan Lawang, Kabupaten Malang",
            "Disaster": "tanah longsor",
        },
        "koordinat": (-7.7956, 112.4622),
    },
    {
        "id_laporan": "LPR-C9D0E1F2",
        "sumber": "teks",
        "ringkasan": "Abrasi pantai merusak tanggul pesisir Tuban.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081999900777",
        "hari_lalu": 6,
        "entitas": {
            "Person": "Warga Tuban",
            "Date": "3 Oktober 2026",
            "Location": "Kecamatan Tuban, Kabupaten Tuban",
            "Disaster": "aberasi pantai",
        },
        "koordinat": (-6.8950, 112.0510),
    },
    {
        "id_laporan": "LPR-G3H4I5J6",
        "sumber": "teks",
        "ringkasan": "Genangan air hujan setinggi lutut di kawasan Rungkut.",
        "status_verifikasi": "ditolak",
        "status_proses": "selesai",
        "phone": "081000000888",
        "hari_lalu": 7,
        "entitas": {
            "Person": "Warga Rungkut",
            "Date": "2 Oktober 2026",
            "Location": "Kecamatan Rungkut, Surabaya",
            "Disaster": "banjir",
        },
        "koordinat": (-7.3286, 112.7575),
    },
    {
        "id_laporan": "LPR-K7L8M9N0",
        "sumber": "audio",
        "ringkasan": "Laporan audio tidak dapat diubah menjadi teks dengan jelas.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "gagal",
        "phone": None,
        "hari_lalu": 0,
        "entitas": {},
        "koordinat": None,
    },
]

KASUS_DEMO = [
    {
        "id_laporan": "LPR-M3N4O5P6",
        "urgensi": "tinggi",
        "status": "menunggu_penugasan",
        "hari_lalu": 2,
        "penugasan": None,
    },
    {
        "id_laporan": "LPR-Q7R8S9T0",
        "urgensi": "sedang",
        "status": "assigned",
        "hari_lalu": 3,
        "penugasan": {
            "instruksi": "Evakuasi warga terdampak dan pasokkan kebutuhan dasar korban terdampak.",
            "unit": ["BPBD Sidoarjo"],
        },
    },
    {
        "id_laporan": "LPR-U1V2W3X4",
        "urgensi": "rendah",
        "status": "on_progress",
        "hari_lalu": 4,
        "penugasan": {
            "instruksi": "Lakukan penilaian kerusakan bangunan dan petakan titik pengungsian warga.",
            "unit": ["BPBD Surabaya"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Tim tiba di lokasi, 12 rumah terpantau aman dan tidak ada kerusakan struktur.",
                    "foto": None,
                    "status": "on_progress",
                },
                {
                    "deskripsi": "Assessment selesai, koordinasi dengan BPBD Kota Batu untuk penanganan lanjutan.",
                    "foto": "photos/assessment-batu.webp",
                    "status": "completed",
                },
            ],
        },
    },
    {
        "id_laporan": "LPR-Y5Z6A7B8",
        "urgensi": "darurat",
        "status": "selesai",
        "hari_lalu": 5,
        "penugasan": {
            "instruksi": "Buka jalur utama Lawang-Malang, evakuasi warga terjebak, pasokkan tim medis.",
            "unit": ["BPBD Malang"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Material longsor dibersihkan, jalur setengah terbuka untuk kendaraan darurat.",
                    "foto": None,
                    "status": "on_progress",
                },
                {
                    "deskripsi": "Jalur kembali normal, 34 warga dievakuasi tanpa korban jiwa.",
                    "foto": "photos/jalur-lawang.webp",
                    "status": "completed",
                },
            ],
            "penutupan": {
                "status": "disetujui",
                "catatan": "Bukti lapangan lengkap, seluruh warga sudah dievakuasi dengan aman.",
            },
        },
    },
    {
        "id_laporan": "LPR-C9D0E1F2",
        "urgensi": "tinggi",
        "status": "completed",
        "hari_lalu": 6,
        "penugasan": {
            "instruksi": "Perkuat tanggul darurat sepanjang 400 meter di pesisir Tuban.",
            "unit": ["BPBD Malang"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Penguatan tanggul darurat selesai, kondisi pantai terpantau aman.",
                    "foto": "photos/tanggul-tuban.webp",
                    "status": "completed",
                },
            ],
            "penutupan": {
                "status": "ditolak",
                "catatan": "Mohon unggah foto tanggul bagian utara yang belum terlihat.",
            },
        },
    },
]


def _utcnow_offset(days: int) -> datetime:
    return NOW - timedelta(days=days)


def _make_laporan(db, admin: User) -> None:
    for item in DEMO_LAPORAN:
        if db.get(Laporan, item["id_laporan"]) is not None:
            continue

        laporan = Laporan(
            id_laporan=item["id_laporan"],
            sumber_input=item["sumber"],
            konten_teks=item["ringkasan"],
            status_verifikasi=item["status_verifikasi"],
            status_proses=item["status_proses"],
            phone_pelapor=item["phone"],
            pesan_gagal="Audio tidak dapat ditranskripsikan." if item["status_proses"] == "gagal" else None,
            audio_path=(
                f"supabase://media/audio/{item['id_laporan'].lower()}.webm"
                if item["sumber"] == "audio"
                else None
            ),
            tanggal_lapor=_utcnow_offset(item["hari_lalu"]),
        )
        if item["status_verifikasi"] in {"terverifikasi", "ditolak"}:
            laporan.id_admin_verifikator = admin.id_user

        db.add(laporan)
        db.flush()

        jenis = item["entitas"]
        if jenis:
            lat, lon = item["koordinat"]
            for label, nilai in jenis.items():
                db.add(
                    EntitasNer(
                        id_laporan=item["id_laporan"],
                        jenis_entitas=label,
                        nilai_teks=nilai,
                        latitude=lat if label == "Location" else None,
                        longitude=lon if label == "Location" else None,
                    )
                )


def _make_kasus(db, admin: User, pimpinan: User) -> None:
    for item in KASUS_DEMO:
        laporan = db.get(Laporan, item["id_laporan"])
        if laporan is None:
            continue

        kasus = laporan.kasus
        if kasus is None:
            kasus = Kasus(
                id_laporan=item["id_laporan"],
                tingkat_urgensi=item["urgensi"],
                status_kasus=item["status"],
                id_admin_eskalasi=admin.id_user,
                tanggal_eskalasi=_utcnow_offset(item["hari_lalu"]),
            )
            db.add(kasus)
            db.flush()

        penugasan = item["penugasan"]
        if penugasan is None:
            continue

        task = kasus.penugasan
        if task is None:
            task = Penugasan(
                id_kasus=kasus.id_kasus,
                id_pimpinan=pimpinan.id_user,
                instruksi=penugasan["instruksi"],
                tanggal_penugasan=_utcnow_offset(item["hari_lalu"]),
            )
            db.add(task)
            db.flush()

        status_by_case = {
            "assigned": "assigned",
            "on_progress": "on_progress",
            "selesai": "completed",
            "completed": "completed",
        }
        unit_status = status_by_case.get(item["status"], "assigned")

        for nama in penugasan["unit"]:
            unit = db.scalar(
                select(User).where(User.nama.contains(nama), User.role == "bpbd")
            )
            if unit is None:
                continue
            existing = db.get(PenugasanUnit, (task.id_penugasan, unit.id_user))
            if existing is None:
                db.add(
                    PenugasanUnit(
                        id_penugasan=task.id_penugasan,
                        id_bpbd=unit.id_user,
                        status_tugas=unit_status,
                        tanggal_update=_utcnow_offset(item["hari_lalu"]),
                    )
                )
                db.flush()

        lapangan_rows = db.query(LaporanLapangan).filter_by(
            id_penugasan=task.id_penugasan
        ).count()
        for i, report in enumerate(penugasan.get("laporan_lapangan", []), start=1):
            if lapangan_rows:
                continue
            unit = db.scalar(
                select(User).where(
                    User.nama.contains(penugasan["unit"][0]), User.role == "bpbd"
                )
            )
            db.add(
                LaporanLapangan(
                    id_penugasan=task.id_penugasan,
                    id_bpbd=unit.id_user if unit else admin.id_user,
                    deskripsi=report["deskripsi"],
                    foto_path=report["foto"],
                    status_saat_update=report["status"],
                    waktu_update=_utcnow_offset(item["hari_lalu"] - i),
                )
            )

        penutupan = penugasan.get("penutupan")
        if penutupan:
            has_penutupan = (
                db.query(VerifikasiPenutupan)
                .filter_by(id_penugasan=task.id_penugasan)
                .count()
            )
            if not has_penutupan:
                db.add(
                    VerifikasiPenutupan(
                        id_penugasan=task.id_penugasan,
                        id_admin=admin.id_user,
                        status_verifikasi=penutupan["status"],
                        catatan=penutupan["catatan"],
                        tanggal_verifikasi=_utcnow_offset(item["hari_lalu"] - 1),
                    )
                )

        db.flush()


def seed_demo() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == "admin"))
        pimpinan = db.scalar(select(User).where(User.role == "pimpinan"))
        if admin is None or pimpinan is None:
            raise RuntimeError("Jalankan `python -m app.seed` terlebih dahulu.")

        _make_laporan(db, admin)
        _make_kasus(db, admin, pimpinan)
        db.commit()

        laporan = db.query(Laporan).count()
        kasus = db.query(Kasus).count()
        penugasan = db.query(Penugasan).count()
        unit = db.query(PenugasanUnit).count()
        lapangan = db.query(LaporanLapangan).count()
        entitas = db.query(EntitasNer).count()
        penutupan = db.query(VerifikasiPenutupan).count()

    print("Seed data demo selesai:")
    print(f"  laporan              : {laporan}")
    print(f"  entitas_ner          : {entitas}")
    print(f"  kasus                : {kasus}")
    print(f"  penugasan            : {penugasan}")
    print(f"  penugasan_unit       : {unit}")
    print(f"  laporan_lapangan     : {lapangan}")
    print(f"  verifikasi_penutupan : {penutupan}")


if __name__ == "__main__":
    seed_demo()
