"""Runtime settings, read from the environment or a .env file at the repo root."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pure-logic tests can run without pydantic-settings installed
    from pydantic import BaseModel as BaseSettings  # type: ignore[assignment]

    def SettingsConfigDict(**kw):  # type: ignore[no-redef]  # noqa: N802
        return kw


REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", Path(".env")), env_file_encoding="utf-8", extra="ignore"
    )

    model_api_key: str = Field(default="", description="Meta Model API key")
    model_api_base: str = "https://api.meta.ai/v1"

    # Model choices. Spark for fast vision/narration, Wonder for long agent work.
    fast_model: str = "muse-spark-1.3"
    agent_model: str = "muse-wonder-1.0"
    sam_model: str = "sam-3.1"
    image_model: str = "muse-image-1.0"
    asr_model: str = "muse-voice-transcribe-1.0"

    kb_path: Path = REPO_ROOT / "data" / "generated" / "kb.json"
    park_name: str = "Kolmården"
    park_entrance_lat: float = 58.6619  # main entrance, next to Wildfire
    park_entrance_lon: float = 16.4462
    default_language: str = "en"
    request_timeout_s: float = 90.0
    max_image_side: int = 1280  # downscale camera frames before sending (saves credits)


@lru_cache
def get_settings() -> Settings:
    return Settings()
