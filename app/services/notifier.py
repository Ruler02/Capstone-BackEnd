"""Pengiriman ID laporan ke pelapor.

Provider `log` (default) hanya mencatat pesan — dipakai saat development
dan ketika akun WhatsApp API belum tersedia. Provider `fonnte`/`wablas`
diaktifkan lewat env untuk produksi.
"""

import logging
from typing import Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger("sigap.notifier")


class Notifier(Protocol):
    def send(self, phone: str, message: str) -> None: ...


class LogNotifier:
    def send(self, phone: str, message: str) -> None:
        logger.info("NOTIF ke %s: %s", phone, message)


class FonnteNotifier:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def send(self, phone: str, message: str) -> None:
        response = httpx.post(
            "https://api.fonnte.com/send",
            headers={"Authorization": self._api_key},
            data={"target": phone, "message": message},
            timeout=15.0,
        )
        response.raise_for_status()


def build_notifier(settings: Settings) -> Notifier:
    if settings.whatsapp_provider == "log":
        return LogNotifier()
    if settings.whatsapp_provider == "fonnte":
        if not settings.whatsapp_api_key:
            raise ValueError("WHATSAPP_API_KEY wajib diisi untuk provider fonnte")
        return FonnteNotifier(settings.whatsapp_api_key)
    raise ValueError(f"Notifier provider tidak dikenal: {settings.whatsapp_provider}")
