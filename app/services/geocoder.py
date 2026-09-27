"""Geocoding lokasi jadi koordinat untuk Peta Kejadian.

Backend `google` memakai Google Maps Geocoding API (diputuskan tim);
key hanya berada di server. Gagal geocode tidak menjatuhkan laporan —
koordinat dibiarkan NULL dan Admin bisa memperbaikinya lewat edit entitas.
"""

from typing import Protocol

import httpx

from app.core.config import Settings

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class Geocoder(Protocol):
    def geocode(self, query: str) -> tuple[float, float] | None: ...


class FakeGeocoder:
    def geocode(self, query: str) -> tuple[float, float] | None:
        if not query.strip():
            return None
        return (-7.2575, 112.7521)


class GoogleGeocoder:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def geocode(self, query: str) -> tuple[float, float] | None:
        response = httpx.get(
            GOOGLE_GEOCODE_URL,
            params={"address": query, "key": self._api_key, "region": "id"},
            timeout=10.0,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return None
        location = results[0]["geometry"]["location"]
        return (location["lat"], location["lng"])


def build_geocoder(settings: Settings) -> Geocoder:
    if settings.geocoder_backend == "fake":
        return FakeGeocoder()
    if settings.geocoder_backend == "google":
        if not settings.google_maps_api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY wajib diisi untuk backend google")
        return GoogleGeocoder(settings.google_maps_api_key)
    raise ValueError(f"Geocoder backend tidak dikenal: {settings.geocoder_backend}")
