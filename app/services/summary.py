"""Ringkasan entitas NER untuk kebutuhan tampilan.

Backend menyimpan entitas sebagai baris terpisah; tabel dan peta membutuhkan
satu nilai ringkas. Helper ini menyusunnya kembali agar API cukup sekali panggil.
"""

from app.models.entitas import EntitasNer


def bencana_dan_lokasi(entitas: list[EntitasNer]) -> tuple[str, str]:
    bencana = next(
        (e.nilai_teks for e in entitas if e.jenis_entitas == "Disaster"), ""
    )
    lokasi = next(
        (e.nilai_teks for e in entitas if e.jenis_entitas == "Location"), ""
    )
    return bencana, lokasi
