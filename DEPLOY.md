# Rencana Deployment SIGAP — Jalur B3 (Hybrid)

Tanggal: 2026-10-19

## Keputusan yang sudah disepakati

| Komponen | Layanan | Alasan |
|---|---|---|
| Frontend | **Cloudflare Pages** | Static build Vite, gratis, preview per branch |
| Backend API | **Render (Docker)** | FastAPI butuh proses Python yang hidup — Pages static-only tidak bisa |
| Database | **Neon PostgreSQL** | Gratis, autoscaling, branching per preview |
| File (audio/foto) | **Cloudflare R2** | Persisten di luar container, kompatibel S3 |
| NER / ASR | **`fake`** | Model asli tidak muat di free tier; menyusul setelah model siap |

Kenapa bukan Cloudflare penuh: Workers RAM 128 MB dan CPU 10 ms (free) /
1 GB dan 5 mnt (berbayar). NER Indonesia fine-tuned butuh ratusan MB RAM.
SQLAlchemy + psycopg native juga tidak jalan di Workers. Karena itu backend
tetap Python di Render.

## Prasyarat sebelum mulai

- Akun Cloudflare (Pages + R2)
- Akun Neon
- Akun Render
- Kode terpush ke GitHub (`Ruler02/Capstone-BackEnd` + repo frontend)

---

## Tahap 1 — Neon PostgreSQL

1. Buat project → pilih region `ap-southeast-1` (dekat pengguna Indonesia).
2. Salin connection string (mode **Pooled** / endpoint pooler, bukan direct).
   Format: `postgresql://neondb_owner.np:<PASSWORD>@ep-xxx.<region>.neon.tech/neondb?sslmode=require`
3. Simpan `?sslmode=require` — Neon menolak koneksi tanpa TLS.
4. Catat `neon.tech` ini *bukan* hostname lama `supabase.co` yang ternyata
   sudah tidak ada.

### Menjalankan migrasi

Alembic butuh akses langsung ke Postgres. Jalankan dari mesin lokal:

```bash
DATABASE_URL="<neon-uri>" alembic upgrade head
```

Jika tabel sudah ada dari pengerjaan sebelumnya, jangan pakai `upgrade`
(lima `DuplicateTable`). Cukup tandai revisi:

```bash
DATABASE_URL="<neon-uri>" alembic stamp head
```

Lalu isi akun demo:

```bash
DATABASE_URL="<neon-uri>" python -m app.seed
DATABASE_URL="<neon-uri>" python -m app.seed_demo
```

### Branching

Neon membuat branch lewat Dashboard → Branches. Branchnya adalah salinan
snapshot database. Kegunaan utamanya: satu branch per preview deployment
atau per developer, supaya schema experiment tidak mengganggu `main`.

Ini membutuhkan migrasi yang bisa dijalankan ulang dengan aman (idempoten),
yang sudah kita punya lewat guard `if db.get(...) is None` di `seed_demo`.

---

## Tahap 2 — Cloudflare R2

1. Dashboard → R2 → Create bucket, nama: `sigap-media`.
2. Buat API token (My Profile → API Tokens → Create Token) dengan izin
   **Object Read & Write** untuk bucket itu saja.
3. Catat tiga nilai:
   - `R2_ACCOUNT_ID` — di dashboard R2 (halaman overview bucket)
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
4. `STORAGE_BACKEND=r2`.

Catatan: R2 memberi `subdomain` publik gratis, tapi file kita sengaja
**private** (bukti laporan berisi nomor telepon pelapor). Akses dibuka
lewat presigned URL hanya bila frontend perlu menampilkan foto — endpoint
presigned belum ada di kode.

---

## Tahap 3 — Render (backend)

1. New → Web Service → connect repo GitHub `Ruler02/Capstone-BackEnd`.
2. Render membaca `render.yaml` di root. Runtime Docker, health `/healthz`.
3. Environment variables yang harus diisi (lihat `render.yaml`):

| Key | Nilai |
|---|---|
| `DATABASE_URL` | dari Neon (pooled, `sslmode=require`) |
| `SECRET_KEY` | biarkan Render `generateValue` |
| `ALLOWED_ORIGINS` | URL Pages, contoh `https://sigap.pages.dev` |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | dari tahap 2 |

4. Build command otomatis dari Dockerfile. Start command:
   `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Batasan free tier yang harus diketahui

- **Render free tidur setelah idle**. Request pertama setelah tidur bisa
  20–30 detik. Untuk demo ini masih bisa diterima; kalau tidak, naik
  `plan: starter`.
- **ASR/NER tetap `fake`.** Whisper + Transformers tidak muat di RAM free.
  Saat model siap, butuh plan berbayar atau backend ML terpisah.
- Jangan ganti `ASR_BACKEND=whisper` sebelum naik plan — akan OOM di boot.

---

## Tahap 4 — Cloudflare Pages (frontend)

Repo frontend: `SIGAP WEB/SIGAP WEB`.

1. Pages → Create → connect repo frontend.
2. Build settings:

| Field | Nilai |
|---|---|
| Build command | `npm ci && npm run build` |
| Build output dir | `dist` |
| Node | 20+ (Vite 8 butuh ≥20; di mesin lokal Node 18 gagal) |

3. Environment variables:

```
VITE_API_URL=https://<backend-render-url>
```

4. Deploy. URL produksi: `https://<project>.pages.dev`.

Dua catatan konfigurasi yang sudah dikerjakan di kode:

- `src/api/client.js` memakai `BASE_URL` dari `VITE_API_URL`. Nilai kosong
  di development sehingga Vite proxy tetap bekerja — tidak ada perubahan
  perilaku lokal.
- CORS backend harus menyertakan domain Pages itu.

---

## Tahap 5 — Verifikasi end-to-end

Urutan pemeriksaan setelah semua tahap selesai:

1. `GET https://<backend>/healthz` → `{"status":"ok"}`
2. Buka `https://<pages>.pages.dev` → cek CORS (Network tab, tidak boleh
   ada error `Access-Control-Allow-Origin`)
3. Login `admin@sigap.id` → dashboard termuat dari Neon
4. Kirim laporan teks dari halaman pelapor → status `selesai`
5. Verifikasi laporan di admin → eskalasi kasus
6. Pimpinan buat penugasan → BPBD muncul di daftar tugas
7. BPBD update status + upload foto → file masuk ke R2 bucket
8. Cek `GET /api/v1/public/map/incidents` → titik peta muncul

Untuk peta Leaflet, tile OpenStreetMap butuh internet — bukan bagian
dari deployment ini.

---

## Yang belum dikerjakan di tahap ini (perlu putusan terpisah)

- **NER/ASR asli.** Saat model siap, opsi: backend ML terpisah (Modal /
  Replicate) atau upgrade Render + `NER_BACKEND=transformers`. Jalur ini
  menyentuh `app/services/ner.py` dan `asr.py` yang saat ini `fake`.
- **Presigned URL foto.** Frontend belum pernah menampilkan isi foto dari
  bucket; hanya menyimpan path. Perlu endpoint baru bila foto harus tampil.
- **Supabase diganti Neon.** Seluruh `SupabaseStorage` masih ada di kode
  (`STORAGE_BACKEND=supabase`) dan dipertahankan sebagai opsi. `DATABASE_URL`
  yang sekarang menunjuk SQLite lokal, bukan Supabase.
- **Repo frontend di GitHub.** Belum dicek apakah sudah terpush — Pages
  butuh repo terpusat.

---

## Urutan kerja yang disarankan

```
Neon (migrasi + seed)  ─┐
R2 (token)             ─┼→ Render (backend live)  ─→ Pages (frontend)  ─→ E2E check
GitHub repo frontend    ─┘
```

Backend harus hidup dulu sebelum Pages, karena halaman manapun akan
gagal fetch kalau API tidak tersedia.
