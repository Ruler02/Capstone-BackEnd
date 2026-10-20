"""Penyimpanan file unggahan (audio & foto bukti).

Dev: file di `MEDIA_ROOT`. Produksi: bucket persisten (Cloudflare R2 /
Supabase Storage) — disk container bersifat sementara, file hilang saat
redeploy.
"""

import uuid
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.config import Settings


class Storage(Protocol):
    def save(self, data: bytes, filename: str, prefix: str) -> str: ...


class LocalStorage:
    def __init__(self, media_root: str):
        self._root = Path(media_root)

    def save(self, data: bytes, filename: str, prefix: str) -> str:
        suffix = Path(filename).suffix.lower() or ".bin"
        target = self._root / prefix / f"{uuid.uuid4().hex}{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return str(target)


class SupabaseStorage:
    """Simpan file ke bucket private melalui Storage REST API."""

    def __init__(self, url: str, bucket: str, service_role_key: str):
        if not url or not service_role_key:
            raise ValueError(
                "SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY wajib diisi untuk Supabase Storage"
            )
        self._base_url = url.rstrip("/")
        self._bucket = bucket
        self._headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        }

    def save(self, data: bytes, filename: str, prefix: str) -> str:
        suffix = Path(filename).suffix.lower() or ".bin"
        object_path = f"{prefix.strip('/')}/{uuid.uuid4().hex}{suffix}"
        response = httpx.post(
            self._object_url(object_path),
            content=data,
            headers={**self._headers, "Content-Type": "application/octet-stream"},
            timeout=30,
        )
        response.raise_for_status()
        return f"supabase://{self._bucket}/{object_path}"

    def download(self, storage_path: str, destination: Path) -> Path:
        prefix = f"supabase://{self._bucket}/"
        if not storage_path.startswith(prefix):
            raise ValueError("Path Storage tidak cocok dengan bucket yang dikonfigurasi")
        response = httpx.get(
            self._object_url(storage_path.removeprefix(prefix)),
            headers=self._headers,
            timeout=60,
        )
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return destination

    def _object_url(self, object_path: str) -> str:
        encoded_bucket = quote(self._bucket, safe="")
        encoded_path = quote(object_path, safe="/")
        return f"{self._base_url}/storage/v1/object/{encoded_bucket}/{encoded_path}"


class R2Storage:
    """Simpan file ke bucket Cloudflare R2 lewat API kompatibel S3."""

    def __init__(
        self,
        account_id: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
    ):
        if not all([account_id, bucket, access_key_id, secret_access_key]):
            raise ValueError(
                "R2_ACCOUNT_ID, R2_BUCKET, R2_ACCESS_KEY_ID, dan "
                "R2_SECRET_ACCESS_KEY wajib diisi untuk R2Storage"
            )
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install boto3 untuk storage backend r2") from exc
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def save(self, data: bytes, filename: str, prefix: str) -> str:
        suffix = Path(filename).suffix.lower() or ".bin"
        object_path = f"{prefix.strip('/')}/{uuid.uuid4().hex}{suffix}"
        self._client.put_object(
            Bucket=self._bucket, Key=object_path, Body=data
        )
        return f"r2://{self._bucket}/{object_path}"

    def download(self, storage_path: str, destination: Path) -> Path:
        prefix = f"r2://{self._bucket}/"
        if not storage_path.startswith(prefix):
            raise ValueError("Path Storage tidak cocok dengan bucket yang dikonfigurasi")
        obj = self._client.get_object(
            Bucket=self._bucket, Key=storage_path.removeprefix(prefix)
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(obj["Body"].read())
        return destination


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.media_root)
    if settings.storage_backend == "supabase":
        return SupabaseStorage(
            settings.supabase_url,
            settings.supabase_storage_bucket,
            settings.supabase_service_role_key,
        )
    if settings.storage_backend == "r2":
        return R2Storage(
            settings.r2_account_id,
            settings.r2_bucket,
            settings.r2_access_key_id,
            settings.r2_secret_access_key,
        )
    raise ValueError(f"Storage backend tidak dikenal: {settings.storage_backend}")
