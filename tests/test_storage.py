"""Uji adapter penyimpanan tanpa memanggil layanan eksternal sungguhan."""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.storage import R2Storage, SupabaseStorage, build_storage


def test_local_storage_writes_file(tmp_path):
    storage = build_storage(Settings(storage_backend="local", media_root=str(tmp_path)))

    path = storage.save(b"isi-audio", "suara.mp3", "audio")

    assert Path(path).read_bytes() == b"isi-audio"
    assert Path(path).parent.name == "audio"


def test_unknown_storage_backend_rejected():
    with pytest.raises(ValueError, match="tidak dikenal"):
        build_storage(Settings(storage_backend="ftp"))


def test_supabase_backend_requires_credentials():
    with pytest.raises(ValueError, match="wajib diisi"):
        build_storage(Settings(storage_backend="supabase", supabase_url=""))


def test_supabase_object_url_is_percent_encoded():
    storage = SupabaseStorage(
        "https://example.supabase.co", "media", "service-role-key"
    )

    url = storage._object_url("audio/rap ort.webm")

    assert url == (
        "https://example.supabase.co/storage/v1/object/media/audio/rap%20ort.webm"
    )


def test_r2_backend_requires_credentials():
    with pytest.raises(ValueError, match="wajib diisi"):
        build_storage(
            Settings(
                storage_backend="r2",
                r2_account_id="",
                r2_access_key_id="",
                r2_secret_access_key="",
            )
        )


def test_r2_save_uses_s3_client_and_r2_scheme():
    """Verifikasi pemakaian boto3 tanpa menyentuh endpoint R2."""
    boto3 = pytest.importorskip("boto3")
    calls = {}

    class FakeClient:
        def put_object(self, **kwargs):
            calls["put"] = kwargs

        def get_object(self, **kwargs):
            calls["get"] = kwargs
            return {"Body": b"isi-r2"}

    storage = R2Storage("acct123", "sigap-media", "key", "secret")
    storage._client = FakeClient()
    del boto3  # hanya untuk memastikan dependency tersedia

    path = storage.save(b"isi-audio", "suara.mp3", "audio")

    assert path.startswith("r2://sigap-media/audio/")
    assert calls["put"]["Bucket"] == "sigap-media"
    assert calls["put"]["Body"] == b"isi-audio"
    # Object key harus berada di dalam prefix folder.
    assert calls["put"]["Key"].startswith("audio/")
    assert calls["put"]["Key"].endswith(".mp3")


def test_r2_download_rejects_foreign_scheme(tmp_path):
    storage = R2Storage("acct123", "sigap-media", "key", "secret")

    with pytest.raises(ValueError, match="tidak cocok"):
        storage.download("supabase://media/audio/x.webm", tmp_path / "x")
