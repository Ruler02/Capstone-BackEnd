"""Penyimpanan file unggahan (audio & foto bukti).

Dev: file di `MEDIA_ROOT`. Produksi: Supabase Storage, karena disk container
bersifat sementara — file hilang saat redeploy.
"""

import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import Settings


class Storage:
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


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.media_root)
    raise ValueError(f"Storage backend tidak dikenal: {settings.storage_backend}")
