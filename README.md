---
title: SIGAP BNPB API
emoji: 🌊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# SIGAP BNPB Backend

Backend FastAPI untuk **Sistem Ekstraksi Entitas Audio Berita Bencana Alam** pada Capstone Project Sistem Informasi UNESA.

## Cakupan sesuai proposal

Backend ini mengikuti alur yang ada di proposal dan rancangan sistem:

```text
Pelapor (teks/audio)
  → audio preprocessing + Whisper ASR (jika audio)
  → text preprocessing
  → NER (Person, Date, Location, Disaster)
  → ID laporan + notifikasi WhatsApp
  → Admin verifikasi/edit
  → Admin eskalasi menjadi Kasus
  → Pimpinan memberi Penugasan
  → Tim BPBD update status + laporan/foto lapangan
  → Admin verifikasi penutupan
  → Dashboard monitoring + Peta Kejadian
```

Aplikasi memiliki **8 tabel domain persis seperti ERD**: `users`, `laporan`, `entitas_ner`, `kasus`, `penugasan`, `penugasan_unit`, `laporan_lapangan`, `verifikasi_penutupan`. `alembic_version` adalah tabel internal migrasi, bukan tabel domain.

## Menjalankan lokal

Gunakan Python 3.11+ (disarankan Python 3.13 stabil), bukan Python beta.

```bash
py -3.13 -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
.venv\\Scripts\\python.exe -m alembic upgrade head
.venv\\Scripts\\python.exe -m app.seed
.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload
```

Buka dokumentasi interaktif di `http://localhost:8000/docs`.

Akun demo (semua password: `ubah-password-ini`):

| Role | Email |
|---|---|
| Admin | `admin@sigap.id` |
| Pimpinan | `pimpinan@sigap.id` |
| BPBD Surabaya | `bpbd.surabaya@sigap.id` |
| BPBD Malang | `bpbd.malang@sigap.id` |

Ganti password akun demo sebelum digunakan di deployment publik.

## Konfigurasi backend ML

Default `.env.example` memakai fake backend supaya development tidak perlu GPU/model besar:

```env
ASR_BACKEND=fake
NER_BACKEND=fake
GEOCODER_BACKEND=fake
WHATSAPP_PROVIDER=log
STORAGE_BACKEND=local
```

Untuk integrasi produksi:

```env
ASR_BACKEND=whisper
NER_BACKEND=transformers
NER_MODEL_PATH=models/ner-indo-finetuned
GEOCODER_BACKEND=google
GOOGLE_MAPS_API_KEY=<server-side-key>
WHATSAPP_PROVIDER=fonnte
WHATSAPP_API_KEY=<provider-key>
STORAGE_BACKEND=supabase
```

Model ASR/NER dan kredensial **tidak** ditulis ke source code. Google Maps key hanya dipakai backend dan tidak pernah dikirim ke frontend.

## Endpoint utama

Semua endpoint selain health check memakai prefix `/api/v1`.

### Publik (tanpa login)

- `POST /api/v1/public/reports` — multipart teks atau audio, balas `202` + ID laporan
- `GET /api/v1/public/reports/{id}/status` — cek status laporan
- `GET /api/v1/public/reports/{id}` — detail transkripsi dan entitas
- `GET /api/v1/public/map/incidents` — titik lokasi laporan terverifikasi

### Auth

- `POST /api/v1/auth/login` — JWT untuk Admin/Pimpinan/BPBD

### Admin

- `GET /api/v1/admin/reports` — antrian laporan
- `PATCH /api/v1/admin/reports/{id}` — edit teks/entitas Date, Location, Disaster
- `POST /api/v1/admin/reports/{id}/verify` — `verified` atau `rejected`
- `POST /api/v1/admin/cases` — eskalasi laporan terverifikasi
- `GET /api/v1/admin/tasks` — tugas untuk dipantau
- `POST /api/v1/admin/tasks/{id}/verify-closure` — setujui/tolak bukti penutupan

### Pimpinan

- `GET /api/v1/pimpinan/dashboard` — statistik kejadian dan penanganan
- `POST /api/v1/pimpinan/penugasan` — tugaskan kasus ke satu/lebih BPBD
- `GET /api/v1/pimpinan/tasks/progress` — pantau status + riwayat laporan lapangan

### BPBD

- `GET /api/v1/bpbd/tasks` — tugas unit sendiri
- `PATCH /api/v1/bpbd/tasks/{id}/status` — `on_progress` atau `completed`
- `POST /api/v1/bpbd/tasks/{id}/field-reports` — deskripsi + foto bukti

- `GET /healthz` — health check deployment

## Testing

```bash
.venv\\Scripts\\python.exe -m pytest -q
```

Test memakai SQLite in-memory dan fake ASR/NER/geocoder/notifier, sehingga tidak membutuhkan API key, GPU, atau layanan eksternal. State machine diuji untuk mencegah eskalasi ganda, akses lintas-unit, transisi status ilegal, dan penutupan tanpa bukti.

## Deploy (Neon + Cloudflare R2 + Hugging Face Spaces + Cloudflare Pages)

1. Buat database Neon, ambil connection string **pooled** dengan
   `postgresql+psycopg://...` dan `sslmode=require`. Migrasi sudah
   dijalankan ke Neon.
2. Buat bucket R2 `sigap-media` + API token Object Read & Write.
3. Buat **Hugging Face Space** bertipe **Docker** dari repository ini;
   `README.md` sudah punya frontmatter `sdk: docker` dan `app_port: 7860`.
4. Isi Space **Secrets**: `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_ORIGINS`,
   `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.
   Isi Space **Variables**: `NER_BACKEND=transformers`,
   `NER_MODEL_PATH=/srv/app/Model-20261025T155233Z-1-001/Model`,
   `STORAGE_BACKEND=r2`, `R2_BUCKET=sigap-media`, `ASR_BACKEND=fake`,
   `APP_ENV=production`.
5. `alembic upgrade head` dijalankan saat container start sebelum Uvicorn.
6. Arahkan frontend Pages ke `https://<space-url>.hf.space/api/v1` lewat
   `VITE_API_URL`, dan masukkan URL Pages itu ke `ALLOWED_ORIGINS`.

Checkpoint model ±484 MB **tidak** ikut GitHub (`.gitignore`), tetapi
wajib ada di repository Space karena `Dockerfile` melakukan `COPY` folder
model. Push model lewat git-lfs; tanpa itu build Space gagal.

Disk container bersifat ephemeral. Untuk demo lokal gunakan
`STORAGE_BACKEND=local`; untuk deployment gunakan `STORAGE_BACKEND=r2`.

## Struktur kode

- `app/api/` — validasi HTTP dan routing per aktor
- `app/services/` — logika pipeline dan adapter layanan luar
- `app/models/` — mapping ERD SQLAlchemy
- `app/schemas/` — kontrak request/response Pydantic
- `app/core/` — config, database, JWT, dependency role
- `tests/` — unit dan integration tests
- `docs/superpowers/specs/` — spesifikasi desain dari proposal
- `docs/superpowers/plans/` — urutan implementasi
