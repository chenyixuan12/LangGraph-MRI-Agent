from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MRI Agent"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("../data")
    cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 512
    allowed_file_extensions: str = ".png,.jpg,.jpeg,.tif,.tiff,.bmp,.dcm,.dicom,.nii,.nii.gz"
    model_dir: Path = Path("../models")
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "mri_agent"
    mongodb_server_selection_timeout_ms: int = 5000

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MRI_", extra="ignore")

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def allowed_extensions(self) -> tuple[str, ...]:
        return tuple(
            extension.strip().lower()
            for extension in self.allowed_file_extensions.split(",")
            if extension.strip()
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    return settings
