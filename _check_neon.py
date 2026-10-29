"""Verifikasi read-only terhadap database Neon.

Tidak menulis apa pun: hanya membaca daftar tabel, jumlah baris, dan
versi Alembic. Kredensial tidak pernah dicetak.

Pemakaian:
    .venv\\Scripts\\python.exe _check_neon.py

Script akan menanyakan connection string. Tempel lalu tekan Enter.
"""

import sys

sys.path.insert(0, r"C:/Users/Khai/Downloads/sigap-bnpb-backend-recovered")

EXPECTED_TABLES = {
    "users",
    "laporan",
    "entitas_ner",
    "kasus",
    "penugasan",
    "penugasan_unit",
    "laporan_lapangan",
    "verifikasi_penutupan",
}


def from_clipboard() -> str:
    """Baca clipboard PowerShell. Dipakai kalau paste ke terminal tidak masuk."""
    import subprocess

    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    value = (out.stdout or "").strip()
    # Hanya terima nilai yang terlihat seperti connection string.
    if "://" in value and len(value) > 20:
        return value
    return ""


def read_url() -> str:
    # 1) file lokal yang sudah di-gitignore
    try:
        stored = open(".neon_url", encoding="utf-8").read().strip()
        if stored:
            return stored
    except OSError:
        pass

    # 2) argumen command line
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()

    # 3) clipboard (paling mudah: copy connection string, lalu jalankan script)
    print("Mencoba membaca connection string dari clipboard ...")
    clip = from_clipboard()
    if clip:
        print("Ditemukan di clipboard (connection string tidak dicetak).")
        return clip

    # 4) minta input interaktif
    print("Clipboard tidak berisi connection string. Tempel lalu tekan Enter:")
    return input("> ").strip()


def to_psycopg(url: str) -> str:
    """Prefiks '+psycopg' hanya untuk SQLAlchemy; psycopg mentah butuh 'postgresql://'."""
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url[len("postgresql+psycopg://") :]
    return url


def main() -> None:
    raw = read_url()
    if not raw:
        raise SystemExit("Connection string kosong.")

    import psycopg

    url = to_psycopg(raw)

    with psycopg.connect(url, connect_timeout=25) as conn:
        with conn.cursor() as cur:
            cur.execute("select version()")
            print("server:", cur.fetchone()[0][:60])

            cur.execute("select current_database(), current_user")
            db, user = cur.fetchone()
            print(f"database={db}  user={user}")

            # Hanya label host, tanpa kredensial. `server_hostname` tidak ada
            # di Neon, jadi pakai alamat server yang dipakai koneksi ini.
            cur.execute("select host(inet_server_addr())")
            addr = cur.fetchone()[0]
            print("server_addr:", addr if addr else "(pooler, alamat tidak dilaporkan)")

            cur.execute(
                "select table_name from information_schema.tables "
                "where table_schema='public' and table_type='BASE TABLE' order by 1"
            )
            tables = {row[0] for row in cur.fetchall()}
            print("\ntabel di schema public:", len(tables))
            for name in sorted(tables):
                print("  -", name)

            print(
                "\nskema domain cocok dengan 8 tabel ERD:",
                EXPECTED_TABLES.issubset(tables),
            )
            missing = sorted(EXPECTED_TABLES - tables)
            if missing:
                print("BELUM ADA:", ", ".join(missing))

            print("\njumlah baris:")
            for name in sorted(EXPECTED_TABLES & tables):
                cur.execute(f"select count(*) from {name}")
                print(f"  {name:24} {cur.fetchone()[0]}")

            if "alembic_version" in tables:
                cur.execute("select version_num from alembic_version")
                print(
                    "\nalembic_version:",
                    [row[0] for row in cur.fetchall()],
                )
            else:
                print("\nalembic_version: TIDAK ADA")


if __name__ == "__main__":
    main()
