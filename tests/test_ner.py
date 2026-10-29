"""Pengujian NER: pemetaan label, dispatch backend, dan model nyata bila ada.

Model BERT-CRF berukuran ±500 MB dan butuh torch. Karena itu tes model nyata
dijaga keberadaan foldernya; kalau folder tidak ada, tes dilewati sehingga
suite tetap bisa dijalankan di mesin tanpa model (misal CI).
"""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.ner import FakeNer, build_ner
from app.services.ner_bert_crf import LABEL_TO_ENTITY_TYPE

MODEL_PATH = (
    Path(__file__).resolve().parents[1]
    / "Model-20261025T155233Z-1-001"
    / "Model"
)
HAS_MODEL = (MODEL_PATH / "best_model.pt").exists()


def test_pemetaan_label_menutupi_empat_kategori():
    """Setiap kategori proposal punya pasangan label di model (BIO)."""
    assert set(LABEL_TO_ENTITY_TYPE.values()) == {
        "Person",
        "Date",
        "Location",
        "Disaster",
    }


def test_label_organisasi_sengaja_tidak_dipakai():
    """ORG ada pada model, tapi proposal hanya mengenali empat kategori."""
    assert "ORG" not in LABEL_TO_ENTITY_TYPE


def test_backend_fake_dipakai_ketika_transformers_tidak_diinginkan():
    settings = Settings(_env_file=None, ner_backend="fake")
    engine = build_ner(settings)
    assert isinstance(engine, FakeNer)


def test_backend_transformers_wajib_punya_path_model():
    settings = Settings(_env_file=None, ner_backend="transformers", ner_model_path="")
    with pytest.raises(ValueError, match="NER_MODEL_PATH"):
        build_ner(settings)


def test_backend_tidak_dikenal_ditolak():
    settings = Settings(_env_file=None, ner_backend="transformers2")
    with pytest.raises(ValueError, match="tidak dikenal"):
        build_ner(settings)


@pytest.mark.skipif(not HAS_MODEL, reason="model BERT-CRF tidak tersedia di mesin ini")
def test_model_nyata_mengekstrak_entitas_dari_teks_indonesia():
    """Model harus menemukan bencana, lokasi, orang, dan tanggal."""
    settings = Settings(
        _env_file=None,
        ner_backend="transformers",
        ner_model_path=str(MODEL_PATH),
    )
    engine = build_ner(settings)

    teks = (
        "Banjir besar melanda Jalan Kenjeran, Surabaya pada 21 Oktober 2026. "
        "Rina Wijaya melaporkan tiga rumah terendam."
    )
    hasil = engine.extract(teks)

    jenis = {e.jenis_entitas for e in hasil}
    assert "Disaster" in jenis, f"entitas yang ditemukan: {[e.nilai_teks for e in hasil]}"
    assert "Location" in jenis
    assert "Person" in jenis
    assert "Date" in jenis


@pytest.mark.skipif(not HAS_MODEL, reason="model BERT-CRF tidak tersedia di mesin ini")
def test_model_nyata_menggabungkan_subword():
    """Sub-word WordPiece harus menyatu jadi satu entitas, bukan terpecah."""
    settings = Settings(
        _env_file=None,
        ner_backend="transformers",
        ner_model_path=str(MODEL_PATH),
    )
    engine = build_ner(settings)

    hasil = engine.extract(
        "Banjir besar melanda Jalan Kenjeran, Surabaya pada 21 Oktober 2026."
    )
    lokasi = [e.nilai_teks for e in hasil if e.jenis_entitas == "Location"]

    # "Kenjeran" ditulis model sebagai "ken" + "##je" + "##ran".
    assert any("Kenjeran" in nilai for nilai in lokasi), lokasi
    assert not any(nilai.startswith("ken") for nilai in lokasi), lokasi


@pytest.mark.skipif(not HAS_MODEL, reason="model BERT-CRF tidak tersedia di mesin ini")
def test_model_nyata_mengembalikan_posisi_karakter_asli():
    """Posisi karakter harus menunjuk ke teks asli, bukan tokenisasi."""
    settings = Settings(
        _env_file=None,
        ner_backend="transformers",
        ner_model_path=str(MODEL_PATH),
    )
    engine = build_ner(settings)

    teks = "Gempa bumi dirasakan warga Kota Probolinggo kemarin."
    hasil = engine.extract(teks)

    assert hasil, "model tidak menemukan entitas apa pun"
    for entitas in hasil:
        potongan = teks[entitas.char_start : entitas.char_end]
        assert potongan == entitas.nilai_teks


@pytest.mark.skipif(not HAS_MODEL, reason="model BERT-CRF tidak tersedia di mesin ini")
def test_engine_diangkat_ulang_dari_cache():
    """Model 500 MB harus dimuat sekali, bukan satu kali per laporan."""
    from app.services.ner import _ENGINE_CACHE

    settings = Settings(
        _env_file=None,
        ner_backend="transformers",
        ner_model_path=str(MODEL_PATH),
    )
    pertama = build_ner(settings)
    kedua = build_ner(settings)
    assert pertama is kedua
