"""Generator ID laporan publik.

Format LPR-XXXXXXXX dengan alphabet tanpa karakter mirip (0/O, 1/I) supaya
aman dibaca dan diketik ulang pelapor saat cek status.
"""

import secrets

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
PREFIX = "LPR-"


def generate_report_id() -> str:
    return PREFIX + "".join(secrets.choice(ALPHABET) for _ in range(8))
