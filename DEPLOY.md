# Rencana Deployment SIGAP — Jalur B3 (Hybrid)

Tanggal: 2026-10-19

## Keputusan yang sudah disepakati

| Komponen | Layanan | Alasan |
|---|---|---|
| Frontend | **Cloudflare Pages** | Static build Vite, gratis, preview per branch |
| Backend API + NER | **Hugging Face Spaces (Docker SDK)** | Bisa menjalankan Docker + model NER BERT-CRF; RAM jauh lebih besar dari Render Free |
| Database | **Neon PostgreSQL** | Gratis, autoscaling, branching per preview |
| File (audio/foto) | **Cloudflare R2** | Persisten di luar container, kompatibel S3 |
| NER / ASR | **NER: `transformers` (model tim)** · **ASR: `fake`** | Model NER sudah dilatih dan dipakai; Whisper masih `fake` karena model ASR belum siap |

Kenapa bukan Cloudflare penuh: Workers RAM 128 MB dan CPU 10 ms (free) /
1 GB dan 5 mnt (berbayar). NER Indonesia fine-tuned butuh ratusan MB RAM.
SQLAlchemy + psycopg native juga tidak jalan di Workers. Karena itu backend
tetap Python di Docker.

Kenapa bukan Render: Render Free hanya menyediakan 512 MB RAM, sedangkan
BERT-base (±506 MB checkpoint) plus torch/transformers saat inferensi butuh
beberapa kali lipat angka itu. HF Spaces Docker memberi ruang yang cukup.

## Prasyarat sebelum mulai

- Akun Cloudflare (Pages + R2)
- Akun Neon
- Akun Hugging Face (untuk Spaces Docker)
- Kode terpush ke GitHub (`Ruler02/Capstone-BackEnd` + repo frontend)

---

## Tahap 1 — Neon PostgreSQL

1. Buat project → pilih region `ap-southeast-1` (dekat pengguna Indonesia).
2. Salin connection string (mode **Pooled** / endpoint pooler, bukan direct).
3. **Tambahkan prefiks driver `+psycopg`.** Neon memberi string
   `postgresql://...`, tetapi aplikasi hanya memasang driver **psycopg3**
   (bukan psycopg2), jadi SQLAlchemy tidak akan menemukan driver dan startup
   gagal. Format yang benar:

   `postgresql+psycopg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`

4. Simpan `?sslmode=require` — Neon menolak koneksi tanpa TLS.
5. Catat `neon.tech` ini *bukan* hostname lama `supabase.co` yang ternyata
   sudah tidak ada.
6. **Rotasi password Neon sebelum dipakai produksi.** Kalau connection string
   pernah dibagikan lewat chat, email, atau commit, anggap password itu
   bocor: Dashboard → project → **Reset password** → pakai string baru
   hanya di Space Secret dan file lokal yang gitignored (`.neon_url`).
   Jangan pernah menulis password baru ke repo atau chat.

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

## Tahap 3 — Hugging Face Spaces (backend)

Space memakai **Docker SDK**. `README.md` sudah dibekali frontmatter
`sdk: docker` dan `app_port: 7860`.

1. Buat Space baru → **Docker** → connect repository
   `Ruler02/Capstone-BackEnd`.
2. HF membaca `Dockerfile` di root. Container wajib mendengarkan
   `0.0.0.0:$PORT`; CMD sudah benar:
   `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Environment variable: **Secret** (tidak pernah dicetak/dikirim) vs
   **Variable** (nilai non-rahasia).

| Tipe | Key | Nilai |
|---|---|---|
| Secret | `DATABASE_URL` | dari Neon (pooled, `postgresql+psycopg://`, `sslmode=require`) |
| Secret | `SECRET_KEY` | string acak panjang, dibuat sekali di dashboard |
| Secret | `ALLOWED_ORIGINS` | URL Pages + URL Space, dipisah koma |
| Secret | `R2_ACCOUNT_ID` | dari tahap 2 |
| Secret | `R2_ACCESS_KEY_ID` | dari tahap 2 |
| Secret | `R2_SECRET_ACCESS_KEY` | dari tahap 2 |
| Variable | `NER_BACKEND` | `transformers` |
| Variable | `NER_MODEL_PATH` | `/srv/app/Model-20261025T155233Z-1-001/Model` |
| Variable | `STORAGE_BACKEND` | **`local`** (fase 1; ganti `r2` di fase 2) |
| Variable | `R2_BUCKET` | `sigap-media` |
| Variable | `ASR_BACKEND` | `fake` |
| Variable | `APP_ENV` | `production` |
| Variable | `GEOCODER_BACKEND` | `fake` |
| Variable | `WHATSAPP_PROVIDER` | `log` |

### Fase storage: local dulu, R2 menyusul

`build_storage()` dipanggil di **setiap** `POST /api/v1/public/reports`
(`app/api/public.py`), termasuk laporan teks yang tidak butuh file.
`R2Storage` melempar `ValueError` saat kredensial kosong, sehingga
`STORAGE_BACKEND=r2` tanpa 3 Secret R2 akan membuat **semua** laporan publik
berakhir 500 — bukan hanya unggahan audio.

Urutan yang aman:

1. **Fase 1 — `STORAGE_BACKEND=local`.** API login, lapor, peta, admin,
   penugasan langsung terverifikasi tanpa menunggu R2. Risiko: file yang
   tersimpan hilang bila container di-restart (disk container bersifat
   sementara). Cukup untuk demo.
2. **Fase 2 — setelah bucket + token jadi:** isi Secret `R2_ACCOUNT_ID`,
   `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, lalu ganti variabel
   `STORAGE_BACKEND` jadi `r2` dan redeploy.

### Catatan penting

- **Checkpoint model ikut di repo (GitHub dan Space) lewat Git LFS.**
  Ukuran `best_model.pt` ±484 MB melebihi batas file GitHub 100 MB, jadi
  `.gitattributes` menandai `*.pt` sebagai LFS. Folder `Model-*` sudah
  dikeluarkan dari `.gitignore`. Tanpa file ini di repo, `COPY` di
  Dockerfile gagal dengan `COPY failed: file not found` dan build Space
  berhenti.
- **Torch versi CPU.** `requirements.txt` menambah
  `--extra-index-url https://download.pytorch.org/whl/cpu` dan memaksa
  `torch==2.14.1+cpu`. Tanpa itu pip mengunduh wheel CUDA dari PyPI
  (±2–3 GB) sehingga image melebihi batas build Space.
- **CORS.** Frontend Pages memanggil API Space lintas domain, jadi
  `ALLOWED_ORIGINS` harus memuat URL Pages produksi **dan** URL Space.
- **Migrasi jalan otomatis saat start** (`alembic upgrade head` sebelum
  uvicorn). Pastikan tabel Neon sudah sesuai — lihat catatan `stamp` di
  Tahap 1.
- **RAM.** Angka pasti ruang RAM perlu dibaca dari dashboard Space setelah
  deploy; catat di `DEPLOY_PROGRESS.md`.

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

- **NER BERT-CRF** sudah diintegrasikan dan lulus uji lokal; checkpoint ±484 MB. Rencana: ikut di repository Space lewat git-lfs karena `Dockerfile` melakukan `COPY` folder model. Kalau image/riset build ternyata tidak layak di Spaces, opsi cadangan adalah menaruh checkpoint di R2 lalu mengunduhnya saat build, atau memakai layanan ber-RAM lebih besar — semua alternatif butuh persetujuan sebelum ganti stack.
- **ASR asli** belum diimplementasikan; saat ini tetap `fake`.
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
R2 (token)             ─┼→ HF Spaces (backend live) ─→ Pages (frontend) ─→ E2E check
GitHub repo frontend    ─┘
```

Backend harus hidup dulu sebelum Pages, karena halaman manapun akan
gagal fetch kalau API tidak tersedia.
