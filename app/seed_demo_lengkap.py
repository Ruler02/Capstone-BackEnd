"""Seed data demo tambahan agar presentasi ke dosen terlihat hidup dan bervariasi.

`seed_demo.py` membuat satu alur lengkap per lifecycle. File ini menambah
volume dan variasi: lebih banyak jenis bencana, beberapa wilayah tambahan,
laporan yang gagal diproses, dan kasus dengan status penugasan yang berbeda
sampai penutupan kasus, termasuk satu penugasan yang menyentuh dua unit BPBD.

Idempoten: aman dijalankan berkali-kali karena setiap id_laporan diperiksa
dulu sebelum dibuat.

Cara pakai:
    python -m app.seed_demo_lengkap
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

# `hari_lalu` = berapa hari lalu kejadian itu terjadi. Nilainya dipakai untuk
# mengisi tanggal lapor, tanggal penugasan, dan waktu laporan lapangan.
LAPORAN_TAMBAHAN = [
    {
        "id_laporan": "LPR-D3F4G5H6",
        "sumber": "teks",
        "ringkasan": "Banjir setinggi lutut menggenangi Jalan Ahmad Yani, Perak.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "selesai",
        "phone": "081112220101",
        "hari_lalu": 0,
        "entitas": {
            "Person": "Warga Perak",
            "Date": "21 Oktober 2026",
            "Location": "Perak, Surabaya",
            "Disaster": "banjir",
        },
        "koordinat": (-7.4356, 112.7360),
    },
    {
        "id_laporan": "LPR-J4K5L6M7",
        "sumber": "teks",
        "ringkasan": "Pohon tumbang menutup jalan raya menuju Pujon sejak dini hari.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "selesai",
        "phone": "081222330101",
        "hari_lalu": 0,
        "entitas": {
            "Person": "Warga Pujon",
            "Date": "21 Oktober 2026",
            "Location": "Pujon, Kabupaten Malang",
            "Disaster": "pohon tumbang",
        },
        "koordinat": (-7.9780, 112.4800),
    },
    {
        "id_laporan": "LPR-N8O9P0Q1",
        "sumber": "teks",
        "ringkasan": "Banjir bandang di Kali Lamongan merendam puluhan rumah warga.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "selesai",
        "phone": "081333440101",
        "hari_lalu": 1,
        "entitas": {
            "Person": "Warga Lamongan",
            "Date": "20 Oktober 2026",
            "Location": "Lamongan, Jawa Timur",
            "Disaster": "banjir bandang",
        },
        "koordinat": (-7.0400, 112.4000),
    },
    {
        "id_laporan": "LPR-R2S3T4U5",
        "sumber": "teks",
        "ringkasan": "Gempa bumi magnitudo 5.1 dirasakan kuat oleh warga Kota Probolinggo.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081444550101",
        "hari_lalu": 2,
        "entitas": {
            "Person": "Warga Probolinggo",
            "Date": "19 Oktober 2026",
            "Location": "Kota Probolinggo, Jawa Timur",
            "Disaster": "gempa bumi",
        },
        "koordinat": (-7.8000, 112.9000),
    },
    {
        "id_laporan": "LPR-V6W7X8Y9",
        "sumber": "audio",
        "ringkasan": "Gelombang tinggi setinggi empat meter menghantam pesisir Pacitan.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081555660101",
        "hari_lalu": 2,
        "entitas": {
            "Person": "Nelayan Pacitan",
            "Date": "19 Oktober 2026",
            "Location": "Pacitan, Jawa Timur",
            "Disaster": "gelombang tinggi",
        },
        "koordinat": (-8.2000, 111.1800),
    },
    {
        "id_laporan": "LPR-Z0A1B2C3",
        "sumber": "teks",
        "ringkasan": "Tanah bergerak di lereng Gunung Arjuno membuat rumah warga retak.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081666770101",
        "hari_lalu": 3,
        "entitas": {
            "Person": "Warga Kota Batu",
            "Date": "18 Oktober 2026",
            "Location": "Kota Batu, Jawa Timur",
            "Disaster": "tanah bergerak",
        },
        "koordinat": (-7.9000, 112.5300),
    },
    {
        "id_laporan": "LPR-D4E5F6G7",
        "sumber": "teks",
        "ringkasan": "Asap karhutla tebal menyelimuti Jombang dan mengganggu jarak pandang.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "selesai",
        "phone": "081777880101",
        "hari_lalu": 4,
        "entitas": {
            "Person": "Warga Jombang",
            "Date": "17 Oktober 2026",
            "Location": "Jombang, Jawa Timur",
            "Disaster": "karhutla",
        },
        "koordinat": (-7.5500, 112.1500),
    },
    {
        "id_laporan": "LPR-H8I9J0K1",
        "sumber": "teks",
        "ringkasan": "Banjir lokal menggenangi akses jalan utama di Manyar sepanjang 300 meter.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081888990101",
        "hari_lalu": 5,
        "entitas": {
            "Person": "Warga Manyar",
            "Date": "16 Oktober 2026",
            "Location": "Manyar, Kabupaten Gresik",
            "Disaster": "banjir",
        },
        "koordinat": (-7.4500, 112.8000),
    },
    {
        "id_laporan": "LPR-L2M3N4O5",
        "sumber": "teks",
        "ringkasan": "Kenaikan muka air laut 40 cm terpantau di pesisir Pasuruan.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081999000101",
        "hari_lalu": 6,
        "entitas": {
            "Person": "Warga Pasuruan",
            "Date": "15 Oktober 2026",
            "Location": "Pasuruan, Jawa Timur",
            "Disaster": "kenaikan air laut",
        },
        "koordinat": (-7.6000, 112.7000),
    },
    {
        "id_laporan": "LPR-P6Q7R8S9",
        "sumber": "teks",
        "ringkasan": "Kabel listrik tumbang dan terjadi arus pendek di kawasan Rungkut.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "gagal",
        "phone": "081000110101",
        "hari_lalu": 0,
        "entitas": {},
        "koordinat": None,
        "pesan_gagal": "Koordinat tidak ditemukan, laporan perlu diverifikasi manual.",
    },
    {
        "id_laporan": "LPR-T0U1V2W3",
        "sumber": "audio",
        "ringkasan": "Laporan rekaman suasananya saja, tidak ada narasi kejadian.",
        "status_verifikasi": "ditolak",
        "status_proses": "gagal",
        "phone": None,
        "hari_lalu": 2,
        "entitas": {},
        "koordinat": None,
        "pesan_gagal": "Audio terlalu berisik dan tidak dapat ditranskripsikan.",
    },
    {
        "id_laporan": "LPR-X4Y5Z6A7",
        "sumber": "teks",
        "ringkasan": "Banjir di Jalan Gubeng membuat akses menuju rumah sakit terputus.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081111220202",
        "hari_lalu": 8,
        "entitas": {
            "Person": "Warga Gubeng",
            "Date": "13 Oktober 2026",
            "Location": "Gubeng, Surabaya",
            "Disaster": "banjir",
        },
        "koordinat": (-7.2500, 112.7500),
    },
    {
        "id_laporan": "LPR-B8C9D0E1",
        "sumber": "teks",
        "ringkasan": "Longsor di tebing jalur Wonosari memblokir akses desa.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081222330202",
        "hari_lalu": 9,
        "entitas": {
            "Person": "Warga Wonosari",
            "Date": "12 Oktober 2026",
            "Location": "Wonosari, Kabupaten Kediri",
            "Disaster": "tanah longsor",
        },
        "koordinat": (-7.6500, 112.1000),
    },
    {
        "id_laporan": "LPR-F2G3H4I5",
        "sumber": "teks",
        "ringkasan": "Angin kencang merobek atap rumah warga di kawasan Socari.",
        "status_verifikasi": "terverifikasi",
        "status_proses": "selesai",
        "phone": "081333440202",
        "hari_lalu": 11,
        "entitas": {
            "Person": "Warga Socari",
            "Date": "10 Oktober 2026",
            "Location": "Socari, Surabaya",
            "Disaster": "angin kencang",
        },
        "koordinat": (-7.3700, 112.7900),
    },
    {
        "id_laporan": "LPR-J6K7L8M9",
        "sumber": "teks",
        "ringkasan": "Luapan Sungai Brantas memutus jalur raya Kediri menuju Blitar.",
        "status_verifikasi": "menunggu_verifikasi",
        "status_proses": "selesai",
        "phone": "081444550202",
        "hari_lalu": 12,
        "entitas": {
            "Person": "Warga Kediri",
            "Date": "9 Oktober 2026",
            "Location": "Kediri, Jawa Timur",
            "Disaster": "banjir luapan",
        },
        "koordinat": (-7.7000, 112.0500),
    },
]

# Kasus tambahan dengan variasi status penugasan dan jumlah unit yang ditugaskan.
KASUS_TAMBAHAN = [
    {
        "id_laporan": "LPR-R2S3T4U5",
        "urgensi": "tinggi",
        "status": "menunggu_penugasan",
        "hari_lalu": 2,
        "penugasan": None,
    },
    {
        "id_laporan": "LPR-V6W7X8Y9",
        "urgensi": "sedang",
        "status": "assigned",
        "hari_lalu": 2,
        "penugasan": {
            "instruksi": "Imbau warga pesisir untuk tidak turun ke pantai dan siapkan titik pengungsian.",
            "unit": ["BPBD Mojokerto"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Patroli pantai selesai, tiga keluarga nelayan sudah dipindahkan ke balai desa.",
                    "foto": None,
                    "status": "on_progress",
                },
            ],
        },
    },
    {
        "id_laporan": "LPR-Z0A1B2C3",
        "urgensi": "tinggi",
        "status": "on_progress",
        "hari_lalu": 3,
        "penugasan": {
            "instruksi": "Assessment kerentanan lereng dan evakuasi dini untuk warga di jalur rawan.",
            "unit": ["BPBD Malang"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Tim tiba di lokasi, dua rumah dinyatakan rawan ambruk dan warga sudah dievakuasi.",
                    "foto": "photos/assessment-batu-2.webp",
                    "status": "on_progress",
                },
            ],
        },
    },
    {
        "id_laporan": "LPR-H8I9J0K1",
        "urgensi": "sedang",
        "status": "assigned",
        "hari_lalu": 5,
        "penugasan": {
            "instruksi": "Bersihkan genangan di jalan utama Manyar dan buka jalur akses warga.",
            "unit": ["BPBD Sidoarjo", "BPBD Surabaya"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Pembersihan saluran air dimulai, akses jalan utama sudah setengah terbuka.",
                    "foto": None,
                    "status": "on_progress",
                },
            ],
        },
    },
    {
        "id_laporan": "LPR-L2M3N4O5",
        "urgensi": "rendah",
        "status": "selesai",
        "hari_lalu": 6,
        "penugasan": {
            "instruksi": "Pantau kondisi tanggul pesisir dan pastikan tidak perlu evakuasi massal.",
            "unit": ["BPBD Mojokerto"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Kondisi tanggul stabil, muka air surut normal, tidak ada korban jiwa.",
                    "foto": "photos/monitor-tanggul-pasuruan.webp",
                    "status": "completed",
                },
            ],
            "penutupan": {
                "status": "disetujui",
                "catatan": "Pemantauan selesai, kondisi tanggul aman dan warga sudah kembali ke rumah.",
            },
        },
    },
    {
        "id_laporan": "LPR-X4Y5Z6A7",
        "urgensi": "darurat",
        "status": "selesai",
        "hari_lalu": 8,
        "penugasan": {
            "instruksi": "Evakuasi warga terdampak di Gubeng dan buka akses menuju rumah sakit.",
            "unit": ["BPBD Surabaya"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Jalan utama dibuka untuk kendaraan ambulans, 12 warga sudah berada di titik aman.",
                    "foto": "photos/evakuasi-gubeng.webp",
                    "status": "completed",
                },
            ],
            "penutupan": {
                "status": "disetujui",
                "catatan": "Akses rumah sakit kembali normal dan seluruh warga telah dievakuasi.",
            },
        },
    },
    {
        "id_laporan": "LPR-B8C9D0E1",
        "urgensi": "tinggi",
        "status": "completed",
        "hari_lalu": 9,
        "penugasan": {
            "instruksi": "Bersihkan material longsoran dan perbaiki jalan desa yang terputus.",
            "unit": ["BPBD Malang"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Material longsoran sudah dibersihkan, jalan desa dapat dilalui kendaraan roda dua.",
                    "foto": "photos/bersih-longsor-wonosari.webp",
                    "status": "completed",
                },
            ],
            "penutupan": {
                "status": "ditolak",
                "catatan": "Foto masih kurang detail, mohon sertakan tampak jalan dari arah berlawanan.",
            },
        },
    },
    {
        "id_laporan": "LPR-F2G3H4I5",
        "urgensi": "rendah",
        "status": "completed",
        "hari_lalu": 11,
        "penugasan": {
            "instruksi": "Bantu perbaikan atap rumah warga dan distribusikan kebutuhan bahan bangunan.",
            "unit": ["BPBD Surabaya"],
            "laporan_lapangan": [
                {
                    "deskripsi": "Perbaikan atap selesai dan material bangunan telah dibagikan ke 18 kepala keluarga.",
                    "foto": "photos/perbaikan-atap-socari.webp",
                    "status": "completed",
                },
            ],
            "penutupan": {
                "status": "disetujui",
                "catatan": "Perbaikan selesai, warga sudah bisa tinggal kembali di rumahnya.",
            },
        },
    },
]


def _utcnow_offset(days: int) -> datetime:
    return NOW - timedelta(days=days)


def _make_laporan(db, admin: User) -> None:
    for item in LAPORAN_TAMBAHAN:
        if db.get(Laporan, item["id_laporan"]) is not None:
            continue

        laporan = Laporan(
            id_laporan=item["id_laporan"],
            sumber_input=item["sumber"],
            konten_teks=item["ringkasan"],
            status_verifikasi=item["status_verifikasi"],
            status_proses=item["status_proses"],
            phone_pelapor=item["phone"],
            pesan_gagal=item.get("pesan_gagal"),
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
    for item in KASUS_TAMBAHAN:
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


def seed_demo_lengkap() -> None:
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

    print("Seed data demo lengkap selesai:")
    print(f"  laporan              : {laporan}")
    print(f"  entitas_ner          : {entitas}")
    print(f"  kasus                : {kasus}")
    print(f"  penugasan            : {penugasan}")
    print(f"  penugasan_unit       : {unit}")
    print(f"  laporan_lapangan     : {lapangan}")
    print(f"  verifikasi_penutupan : {penutupan}")


if __name__ == "__main__":
    seed_demo_lengkap()
