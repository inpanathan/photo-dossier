"""Layered configuration module with startup validation.

Loads config in order of precedence (highest wins):
  1. Environment variables (from .env or system)
  2. Environment-specific YAML file (configs/{APP_ENV}.yaml)
  3. Hardcoded defaults

Fails fast at startup if required values are missing or invalid.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    show_locals: bool = False


class ServerSettings(BaseSettings):
    """Application server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False


class AdminSettings(BaseSettings):
    """Admin console configuration."""

    secret_key: str = "admin-secret-change-me"
    allowed_base_dirs: list[str] = Field(default_factory=lambda: ["data", "static"])
    mounts_file: str = "data/static_mounts.json"


class CorpusSettings(BaseSettings):
    """Photo corpus configuration."""

    corpus_dir: str = "data/corpus"
    supported_formats: list[str] = Field(
        default_factory=lambda: ["jpg", "jpeg", "png", "heic", "heif"]
    )
    max_image_size_mb: int = 50


class InferenceSettings(BaseSettings):
    """Remote inference service configuration (7810 node)."""

    base_url: str = "http://100.111.31.125:8010"
    timeout_seconds: int = 30
    human_model: str = "insightface"
    pet_model: str = "yolov8"
    embedding_model: str = "dinov2"
    min_face_confidence: float = 0.5
    min_pet_confidence: float = 0.4


class IndexSettings(BaseSettings):
    """FAISS vector index configuration."""

    faiss_index_dir: str = "data/indices"
    human_index_file: str = "human.index"
    pet_index_file: str = "pet.index"
    metadata_db_path: str = "data/metadata.db"
    human_similarity_threshold: float = 0.6
    pet_similarity_threshold: float = 0.5
    default_top_k: int = 50
    index_type: str = "flat"
    ivf_nlist: int = 100


class NarrativeSettings(BaseSettings):
    """LLM/VLM narrative generation configuration."""

    llm_base_url: str = "http://localhost:8001/v1"
    llm_model: str = "Qwen/Qwen2.5-14B-Instruct-AWQ"
    llm_max_tokens: int = 4000
    vlm_base_url: str = "http://100.111.31.125:8011/v1"
    vlm_model: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    vlm_max_tokens: int = 500
    temperature: float = 0.3


class JobSettings(BaseSettings):
    """Async job queue configuration."""

    max_concurrent_jobs: int = 4
    job_timeout_seconds: int = 600
    result_ttl_seconds: int = 3600


class UploadSettings(BaseSettings):
    """Photo upload configuration."""

    max_file_size_mb: int = 20
    chunk_size_bytes: int = 1048576
    upload_dir: str = "data/uploads"
    accepted_types: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/heic"]
    )


class SecuritySettings(BaseSettings):
    """Security configuration."""

    rate_limit_rpm: int = 60  # requests per minute per IP (0 = disabled)
    jwt_expiry_seconds: int = 86400  # 24 hours
    require_auth: bool = False  # enable JWT auth on API endpoints


class Settings(BaseSettings):
    """Root application settings.

    Merges environment variables, YAML config, and defaults.
    Validates at startup — the app will not start with invalid config.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # ---- Top-level ----
    app_env: str = "dev"
    app_debug: bool = True
    secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    use_mocks: bool = True
    model_backend: str = "mock"

    # ---- Nested settings ----
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    admin: AdminSettings = Field(default_factory=AdminSettings)
    corpus: CorpusSettings = Field(default_factory=CorpusSettings)
    inference: InferenceSettings = Field(default_factory=InferenceSettings)
    index: IndexSettings = Field(default_factory=IndexSettings)
    narrative: NarrativeSettings = Field(default_factory=NarrativeSettings)
    jobs: JobSettings = Field(default_factory=JobSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = {"dev", "staging", "production", "test"}
        if v not in allowed:
            msg = f"app_env must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("model_backend")
    @classmethod
    def validate_model_backend(cls, v: str) -> str:
        allowed = {"mock", "local", "cloud"}
        if v not in allowed:
            msg = f"model_backend must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        """Fail fast if production config is incomplete."""
        if self.app_env == "production":
            if self.secret_key == "CHANGE-ME-IN-PRODUCTION":
                msg = "SECRET_KEY must be set in production"
                raise ValueError(msg)
            if self.app_debug:
                msg = "APP_DEBUG must be false in production"
                raise ValueError(msg)
        return self


def _load_yaml_config(env: str) -> dict[str, Any]:
    """Load environment-specific YAML config if it exists."""
    config_path = PROJECT_ROOT / "configs" / f"{env}.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def load_settings() -> Settings:
    """Create and validate application settings.

    Merges: defaults < YAML config < environment variables.
    """
    import os

    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")

    env = os.getenv("APP_ENV", "dev")
    yaml_config = _load_yaml_config(env)

    return Settings(**yaml_config)


# Singleton — import this from anywhere
settings = load_settings()
