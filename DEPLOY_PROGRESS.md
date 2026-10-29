# SIGAP Deployment Progress

Terakhir diperbarui: 2026-10-29

## Status: BELUM DEPLOYED — blocker hosting berbayar

Belum ada URL production yang terverifikasi. Backend **sudah terbukti
bekerja sebagai Docker image** (lihat di bawah), tapi belum ada tempat
gratis untuk menjalankannya.

---

## Bukti nyata yang sudah diperoleh

### 1. Docker image berhasil dibangun ✅

```text
[+] Building 512.5s (14/14) FINISHED
 => [4/8] RUN pip install --no-cache-dir -r requirements.txt   398.4s
 => [8/8] COPY Model-20261025T155233Z-1-001/Model ...          1.1s
 => naming to docker.io/library/sigap-api:local
```

Konsekuensi penting: `torch` terpasang dari index CPU (bukan CUDA) —
build集约 398 detik dan image tetap wajar. Jadi perbaikan `requirements.txt`
sudah terbukti benar di build nyata.

### 2. Migrasi Neon jalan dari dalam container ✅

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

Tidak ada `DuplicateTable` → database Neon sudah di revisi `head`
(`925b4dc5ea17`) dan `alembic upgrade head` bersifat no-op yang aman.
Perbaikan driver `postgresql+psycopg://` juga terbukti: Alembic membaca
`PostgresqlImpl`, bukan error driver.

### 3. Tabel Neon terverifikasi (read-only) ✅

9 tabel, `alembic_version = 925b4dc5ea17` (head), isi: 25 laporan,
13 kasus, 11 penugasan, 12 laporan lapangan, 6 user, 88 entitas, 6 penutupan.

### 4. Test suite ✅

```text
47 passed in 70.65s (0:01:10)
```

---

## Bug yang ditemukan & diperbaiki

1. **`$PORT` kosong → container mati.** Uvicorn gagal start dengan
   `Error: Option '--port' requires an argument`. Diperbaiki di
   `Dockerfile`: `--port ${PORT:-7860}`. Image **harus di-build ulang**
   supaya perbaikan masuk.
2. **`requirements.txt` tanpa index CPU** → build menarik CUDA 2–3 GB.
   Diperbaiki: `--extra-index-url .../whl/cpu` + `torch==2.14.1+cpu` +
   `transformers==5.20.2`. Terbukti benar di build nyata (398 s).
3. **`NER_MODEL_PATH` salah** di `DEPLOY.md` / `README.md` /
   `DEPLOY_PROGRESS.md` (`/app/...` vs `WORKDIR /srv/app`). Diperbaiki.
4. **Model 484 MB belum ter-track git** → `COPY` di Dockerfile akan
   gagal. `.gitattributes` (`*.pt filter=lfs`) + `.gitignore` sudah siap.
5. **`STORAGE_BACKEND=r2` tanpa Secret R2 = semua laporan publik 500**
   (`build_storage()` dipanggil di setiap POST di `app/api/public.py:56`).
   Fase 1 pakai `local`; fase 2 ganti ke `r2`.

---

## 🔴 BLOCKER: Hugging Face Spaces butuh langganan PRO

```text
Error: Client error '402 Payment Required' for url
'https://huggingface.co/api/repos/create'

Static Spaces are free for everyone, but hosting Gradio and Docker Spaces
on free cpu-basic requires a PRO subscription.
```

**Bukti:** perintah `hf repos create ... --type space --space-sdk docker
--flavor cpu-basic` ditolak server HF dengan 402. Ini batasan layanan,
bukan kesalahan konfigurasi.

**PILIHAN (perlu keputusan user):**

### Opsi A — HF Spaces PRO (~$9–20/bulan)
- ✅ Tetap di stack yang sudah diputuskan.
- ✅ RAM cukup untuk BERT-CRF.
- ❌ Butuh kartu kredit / langganan.

### Opsi B — Render Free + NER `fake` (gratis)
- ✅ Gratis, Docker + `render.yaml` sudah siap.
- ✅ `render.yaml` sudah dikonfigurasi lengkap.
- ❌ RAM 512 MB **tidak cukup** untuk BERT-base (checkpoint 484 MB + torch).
  NER harus `fake` → ekstraksi entitas otomatis tidak jalan di production.
- ❌ Disk container ephemeral (file hilang saat redeploy).

### Opsi C — Railway / Fly.io (free tier, RAM lebih besar)
- ✅ RAM 512 MB–2 GB, Docker didukung.
- ⚠️ Free tier biasanya butuh kartu kredit dan ada batas usage.

### Opsi D — Pisahkan: backend di Render Free (NER fake) + NER di service terpisah
- ❌ Kompleks, tim kecil, unsustainable untuk capstone.

**Rekomendasi: Opsi B** kalau demo lokal/presentasi sudah cukup — sistem
tetap jalan penuh dengan 4 role, hanya ekstraksi entitas otomatis yang
di-modekan mock. **Opsi A** kalau NER sungguhan wajib live.

> Catatan: keputusan ini **tidak saya ambil sendiri** karena menyangkut
> biaya (dilarang tanpa persetujuan).

---

## Perintah yang harus dijalankan user (PowerShell)

### ① Build ulang image (perbaikan `$PORT`)

```powershell
cd C:\Users\Khai\Downloads\sigap-bnpb-backend-recovered
docker build -t sigap-api:local .
```

### ② Jalankan container uji (sekarang port aman)

```powershell
docker rm -f sigap-test 2>$null
docker run -d --name sigap-test -p 8000:7860 `
  -e DATABASE_URL="postgresql+psycopg://neondb_owner:npg_dj1sAz8HxSvr@ep-little-boat-b39ywrfb-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require" `
  -e SECRET_KEY="uji-lokal-saja-minimal-32-karakter-panjang" `
  -e APP_ENV=production `
  -e STORAGE_BACKEND=local `
  -e ASR_BACKEND=fake `
  -e NER_BACKEND=transformers `
  -e NER_MODEL_PATH=/srv/app/Model-20261025T155233Z-1-001/Model `
  -e ALLOWED_ORIGINS=http://localhost:5173 `
  sigap-api:local
```

### ③ Cek log (harus muncul "Uvicorn running")

```powershell
docker logs sigap-test --tail 30
```

### ④ Uji endpoint (pakai `curl.exe`, bukan `curl` alias PowerShell)

```powershell
curl.exe http://localhost:8000/healthz
curl.exe -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"email\":\"admin@sigap.id\",\"password\":\"ubah-password-ini\"}"
curl.exe http://localhost:8000/api/v1/public/map/incidents
```

### ⑤ Ukur RAM saat inferensi NER

```powershell
curl.exe -X POST http://localhost:8000/api/v1/public/reports -F "konten_teks=Banjir besar di Surabaya pada 21 Oktober 2026" -F "phone_pelapor=08123456789"
docker stats sigap-test --no-stream
```

### ⑥ Commit + push (termasuk model via LFS)

```powershell
cd C:\Users\Khai\Downloads\sigap-bnpb-backend-recovered
git add -A
git lfs install
git status
git commit -m "feat: integrasi NER BERT-CRF dan kesiapan deployment"
git push origin main
```

Cek LFS dulu: `git lfs ls-files` harus menampilkan `best_model.pt`.

### ⑦ Bucket R2 (dashboard Cloudflare)

- R2 → **Create bucket** → `sigap-media`
- R2 → **Manage R2 API Tokens** → Create → Object Read & Write → bucket
  `sigap-media` → salin `Account ID`, `Access Key ID`, `Secret Access Key`
- Ketiganya **langsung isi ke dashboard hosting** (Render/Space), jangan
  kirim lewat chat.

### ⑧ Rotasi password Neon (WAJIB — pernah muncul di chat)

- Neon Dashboard → project → **Reset password**
- String baru hanya ke Secret hosting + file lokal `.neon_url` (gitignored).

### ⑨ Frontend Pages (setelah backend live)

- Cloudflare → Pages → Create → connect repo frontend
- Env: `VITE_API_URL=https://<url-backend>`
- `ALLOWED_ORIGINS` di hosting memuat URL Pages + URL backend

---

## Status per file (semua belum di-commit)

```text
 M .dockerignore      M .env.example       M .gitignore
 M DEPLOY.md          M Dockerfile         M README.md
 M app/core/config.py M app/services/ner.py M render.yaml
 M requirements.txt   M tests/test_pipeline.py

 ?? .gitattributes    ?? DEPLOY_PROGRESS.md ?? _check_neon.py
 ?? app/services/ner_bert_crf.py            ?? tests/test_ner.py
 ?? Model-20261025T155233Z-1-001/
```

---

## Yang belum bisa diverifikasi

- RAM produksi (belum ada hosting aktif).
- URL production + CORS frontend.
- Upload foto ke R2 (bucket belum dibuat).
- Ukuran image final di registry (build lokal ≈ 1.5–2 GB perkiraan; angka
  resmi belum diukur karena `docker images` belum sempat dijalankan).
