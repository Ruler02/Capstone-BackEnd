"""Konfigurasi terpusat: semua nilai berasal dari environment variable.

Satu tempat membaca konfigurasi membuat kode yang sama bisa jalan di laptop
(dev, model fake) maupun di server produksi (Supabase, Whisper) tanpa diubah.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SIGAP BNPB"
    app_env: str = "development"
    secret_key: str = "dev-secret-ganti-sebelum-produksi"
    access_token_expire_minutes: int = 1440

    database_url: str = "sqlite:///./sigap.db"

    asr_backend: str = "fake"
    ner_backend: str = "fake"
    ner_model_path: str = ""
    geocoder_backend: str = "fake"
    google_maps_api_key: str = ""

    whatsapp_provider: str = "log"
    whatsapp_api_key: str = ""

    storage_backend: str = "local"
    media_root: str = "./media"
    supabase_url: str = ""
    supabase_storage_bucket: str = "media"

    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
